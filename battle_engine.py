
"""
OPERATION COMMANDER
Battle Engine V1 (Foundation)

Purpose:
Combine higher-level engine outputs into a battlefield state.
This engine NEVER generates BUY CALL / BUY PUT.
"""

from dataclasses import dataclass

@dataclass
class BattleState:
    zone:str
    battle_score:int
    commander_status:str
    confidence:float
    reasons:list

def evaluate(*,
             above_pdc:bool,
             above_vwap:bool,
             above_ema75:bool,
             opening_range_break:str,
             premium_flow:str,
             straddle_structure:str):
    score=0
    reasons=[]

    if above_pdc:
        score+=1; reasons.append("Above PDC")
    if above_vwap:
        score+=1; reasons.append("Above VWAP")
    if above_ema75:
        score+=1; reasons.append("Above EMA75")

    if opening_range_break=="UP":
        score+=2; reasons.append("OR High Broken")
    elif opening_range_break=="DOWN":
        score+=2; reasons.append("OR Low Broken")

    if premium_flow=="CALL":
        score+=2; reasons.append("Call Premium Migration")
    elif premium_flow=="PUT":
        score+=2; reasons.append("Put Premium Migration")

    if straddle_structure=="LONG_STRADDLE":
        zone="EXPANSION_ZONE"
    elif straddle_structure=="SHORT_STRADDLE":
        zone="DECAY_ZONE"
    else:
        zone="RANGE_WAR"

    if score>=6:
        status="ATTACK"
    elif score>=3:
        status="WAIT"
    else:
        status="HOLD_FIRE"

    return BattleState(
        zone=zone,
        battle_score=score,
        commander_status=status,
        confidence=min(score*12.5,100),
        reasons=reasons
    )

if __name__=="__main__":
    r=evaluate(
        above_pdc=True,
        above_vwap=True,
        above_ema75=True,
        opening_range_break="UP",
        premium_flow="CALL",
        straddle_structure="LONG_STRADDLE",
    )
    print(r)
