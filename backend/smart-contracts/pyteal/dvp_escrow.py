"""
Algorand PyTeal Smart Contract: DVP Escrow
Enables atomic delivery-vs-payment settlements
"""

from pyteal import *

def dvp_escrow_contract():
    """
    DVP Escrow Contract
    
    Flow:
    1. Seller deposits ASA tokens
    2. Buyer deposits USDC
    3. Atomic swap executed
    4. Both parties receive assets simultaneously
    """
    
    # Global state
    seller_address = Bytes("seller")
    buyer_address = Bytes("buyer")
    asset_id = Bytes("asset_id")
    payment_amount = Bytes("payment_amount")
    is_locked = Bytes("is_locked")
    
    # Initialize contract
    on_initialize = Seq([
        App.globalPut(seller_address, Txn.sender()),
        App.globalPut(asset_id, Txn.assets[0]),
        App.globalPut(payment_amount, Int(0)),
        App.globalPut(is_locked, Int(0)),
        Return(Int(1))
    ])
    
    # Seller deposits ASA
    on_deposit_asset = Seq([
        Assert(
            And(
                Txn.sender() == App.globalGet(seller_address),
                Global.group_size() == Int(2),
                Gtxn[1].type_enum() == TxnType.AssetTransfer,
                Gtxn[1].xfer_asset() == App.globalGet(asset_id)
            )
        ),
        App.globalPut(is_locked, Int(1)),
        Return(Int(1))
    ])
    
    # Buyer deposits USDC + execute swap
    on_swap = Seq([
        Assert(
            And(
                App.globalGet(is_locked) == Int(1),
                Global.group_size() == Int(3),
                # Buyer payment
                Gtxn[0].type_enum() == TxnType.Payment,
                Gtxn[0].amount() == App.globalGet(payment_amount),
                Gtxn[0].receiver() == App.globalGet(seller_address),
                # Asset transfer to buyer
                Gtxn[1].type_enum() == TxnType.AssetTransfer,
                Gtxn[1].xfer_asset() == App.globalGet(asset_id),
                Gtxn[1].asset_receiver() == App.globalGet(buyer_address)
            )
        ),
        # Mark swap complete
        App.globalPut(is_locked, Int(0)),
        Return(Int(1))
    ])
    
    program = Cond(
        [Txn.application_id() == Int(0), on_initialize],
        [Txn.on_completion() == OnComplete.NoOp, Cond(
            [Txn.application_args[0] == Bytes("deposit"), on_deposit_asset],
            [Txn.application_args[0] == Bytes("swap"), on_swap]
        )],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(Int(1))]
    )
    
    return program

if __name__ == "__main__":
    print(compileTeal(dvp_escrow_contract(), Mode.Application, version=6))