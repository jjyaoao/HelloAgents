"""Demo: mint a verifiable receipt link for an agent output.

Requires:
  export C2C_API_KEY=...
  export C2C_BOT_ID=bot_...
"""
import os
from claw2claw_receipt import create_offer, create_job, post_receipt


def main():
    bot_id = os.environ["C2C_BOT_ID"]

    offer = create_offer(
        seller_bot_id=bot_id,
        title="HelloAgents: proof-of-delivery demo",
        description="Demo: mint a verifiable receipt for an agent output.",
        price_cents=0,
        tags=["demo"],
        capabilities=["receipt_demo"],
    )

    job = create_job(offer_id=offer["offerId"], buyer_bot_id=bot_id, idempotency_key="helloagents_demo_v1")

    proof = post_receipt(
        job_id=job["jobId"],
        status="ok",
        artifacts={"result.md": "# HelloAgents\n\nThis agent output now has a verifiable receipt.\n"},
    )

    print("Proof link:", proof["proofUrl"])


if __name__ == "__main__":
    main()
