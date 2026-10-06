import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from hello_agents import HelloAgentsLLM, RunBudget, BudgetExceeded
from hello_agents.storage import backup_database, migrate_database, SchemaVersionError
from hello_agents.memory import MemoryStore, ProfileStore, ProfileModel
from hello_agents.retrieval.evaluation import ranking_metrics, evaluate_retrieval
from hello_agents.retrieval.rerank import LLMReranker


def model(budget=None):
    llm = HelloAgentsLLM(budget=budget)
    llm._adapter = Mock()
    llm._adapter.invoke.return_value = SimpleNamespace(content='ok',usage={'total_tokens':3})
    return llm


def test_shared_budget_across_model_instances_and_threads():
    budget = RunBudget(max_calls=2)
    one,two = model(),model()
    with budget.scope():
        one.invoke([])
        asyncio.run(two.ainvoke([]))
        with pytest.raises(BudgetExceeded):
            one.invoke([])
    assert budget.snapshot()['model_calls'] == 2
    assert budget.snapshot()['reported_tokens'] == 6


def test_budget_concurrent_admission_is_atomic():
    budget=RunBudget(max_calls=5)
    def run(_):
        try:
            budget.reserve()
            return True
        except BudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(run,range(30))) == 5


def test_tokens_missing_usage_and_time_stop_later_calls():
    budget=RunBudget(max_tokens=2)
    llm=model(budget)
    llm.invoke([])
    with pytest.raises(BudgetExceeded): llm.invoke([])
    budget=RunBudget(max_tokens=100)
    llm=model(budget)
    llm._adapter.invoke.return_value.usage={}
    llm.invoke([])
    with pytest.raises(BudgetExceeded): llm.invoke([])
    budget=RunBudget(max_seconds=1)
    budget._started-=2
    with pytest.raises(BudgetExceeded): model(budget).invoke([])


def test_memory_purge_scoped_revision_and_backup(tmp_path):
    path=tmp_path/'mem.db'
    one=MemoryStore(str(path),'alice','trip')
    two=MemoryStore(str(path),'bob','trip')
    one.add('private','user')
    two.add('keep','user')
    backup=backup_database(path,tmp_path/'backup.db')
    with pytest.raises(FileExistsError): backup_database(path,backup)
    old=one.revision
    one.add('new','user')
    with pytest.raises(ValueError): one.purge(expected_revision=old)
    assert one.purge(expected_revision=one.revision) == 2
    assert one.export_records() == [] and len(two.export_records()) == 1
    assert len(MemoryStore(str(backup),'alice','trip').export_records()) == 1


def test_schema_migration_rolls_back_and_future_rejected(tmp_path):
    path=tmp_path/'mem.db'
    MemoryStore(str(path),'a','b')
    def broken(db):
        db.execute('CREATE TABLE migration_probe(x INTEGER)')
        raise RuntimeError('failure')
    with pytest.raises(RuntimeError): migrate_database(path,'memory',2,{1:broken})
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='migration_probe'").fetchone() is None
        assert db.execute("SELECT version FROM helloagents_schema WHERE component='memory'").fetchone()[0] == 1
    migrate_database(path,'memory',2,{1:lambda db: db.execute('CREATE TABLE added(x INTEGER)')})
    with pytest.raises(SchemaVersionError): MemoryStore(str(path),'a','b')


def test_profile_purge_does_not_allow_stale_recreation(tmp_path):
    class Profile(ProfileModel):
        interest:str
    store=ProfileStore(str(tmp_path/'profiles.db'),user_id='a',namespace='app',schema=Profile)
    store.put({'interest':'private'},source='user',expected_revision=0)
    assert store.purge_history(expected_revision=1) == 1
    assert 'private' not in str(store.export_history())
    assert store.get() is None
    with pytest.raises(ValueError): store.put({'interest':'stale'},source='user',expected_revision=1)
    store.put({'interest':'new'},source='user',expected_revision=2)


def test_metrics_have_known_values_and_no_answer_is_undefined():
    values=ranking_metrics(['irrelevant','a','b'],{'a':1,'b':1},k=2)
    assert values['recall_at_k']==0.5 and values['mrr_at_k']==0.5
    assert 0 < values['ndcg_at_k'] < 1
    assert ranking_metrics(['a'],{})['recall_at_k'] is None
    assert ranking_metrics(['a','b'],{'a':3,'b':1})['ndcg_at_k']==1
    with pytest.raises(ValueError): ranking_metrics(['a','a'],{'a':1})
    backend=Mock()
    backend.search.return_value=[SimpleNamespace(chunk_id='a')]
    report=evaluate_retrieval(backend,[{'query':'query','relevance':{'a':1}}])
    assert report['mean']['mrr_at_k']==1 and report['evaluated_queries']==1


@pytest.mark.parametrize('text',['[0,0]','[true,0]','[2,0]','{"a":1}'])
def test_reranker_rejects_invalid_model_order(text):
    llm=Mock()
    llm.invoke.return_value=SimpleNamespace(content=text,finish_reason='stop')
    with pytest.raises(ValueError): LLMReranker(llm).rerank('q',[SimpleNamespace(content='a'),SimpleNamespace(content='b')])


def test_reranker_retains_exact_evidence_objects():
    llm=Mock()
    llm.invoke.return_value=SimpleNamespace(content='[1,0]',finish_reason='stop')
    candidates=[SimpleNamespace(content='a'),SimpleNamespace(content='b')]
    assert LLMReranker(llm).rerank('q',candidates)==candidates[::-1]


def test_graph_prune_preserves_active_generation(tmp_path):
    from hello_agents.retrieval.graph.storage import GraphStorage
    store=GraphStorage(str(tmp_path/'graph.db'),'namespace')
    store.publish('old',1,'cfg',{},expected_generation=None)
    store.publish('new',2,'cfg',{},expected_generation='old')
    store.put_cache('key',{'text':'private'})
    assert store.prune(clear_cache=True)=={'generations_removed':1,'cache_entries_removed':1}
    assert store.active()['id']=='new' and store.get_cache('key') is None


def test_qdrant_namespace_purge_keeps_other_store(tmp_path):
    pytest.importorskip('qdrant_client')
    from qdrant_client import QdrantClient
    from hello_agents.retrieval import RAGStore,QdrantSearch,IndexStaleError
    class Embedding:
        model_id='fixture'
        dimension=2
        def embed_documents(self,texts): return [[1.,0.] for _ in texts]
        def embed_query(self,text): return [1.,0.]
    stores=[RAGStore(str(tmp_path/f'{i}.db')) for i in range(2)]
    for store in stores: store.add_document('private data','source')
    client=QdrantClient(':memory:')
    try:
        first,second=[QdrantSearch(store,Embedding(),client=client) for store in stores]
        first.sync();second.sync()
        first.purge_namespace()
        with pytest.raises(IndexStaleError): first.search('private')
        assert len(second.search('private'))==1
        assert first.sync()==1
    finally:
        client.close()


@pytest.mark.asyncio
async def test_tool_thread_inherits_task_budget():
    from hello_agents.tools import Tool
    class ModelTool(Tool):
        def __init__(self): super().__init__('call','call model')
        def get_parameters(self): return []
        def run(self, parameters): return model().invoke([])
    with RunBudget(max_calls=1).scope():
        await ModelTool().arun({})
        with pytest.raises(BudgetExceeded): await ModelTool().arun({})
