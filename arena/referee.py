"""Conservative Syzygy adjudication with rounded DTZ fifty-move semantics."""


def syzygy_decision(tablebase,board):
    if len(board.piece_map())>7 or board.castling_rights:return {'result':None,'note':''}
    try:
        wdl=tablebase.probe_wdl(board)
        if abs(wdl)<2:return {'result':'1/2-1/2','reason':'syzygy_draw','note':'Syzygy WDL50 draw'}
        # WDL50 is defined assuming a zero halfmove counter. At that boundary
        # WDL alone certifies the result, even if a DTZ file is unavailable.
        if board.halfmove_clock==0:
            reason='syzygy_wdl'
        else:
            dtz=tablebase.probe_dtz(board)
            # DTZ50'' may underestimate the distance by one ply. Equality at
            # 100 is not enough to certify a result from a nonzero counter.
            if abs(dtz)+board.halfmove_clock>=100:
                return {'result':None,'note':'Syzygy adjudication deferred near the fifty-move boundary (rounded DTZ).'}
            reason='syzygy_dtz'
        winner=board.turn if wdl>0 else not board.turn
        return {'result':'1-0' if winner else '0-1','reason':reason,'note':'Syzygy WDL50 with a certified fifty-move margin'}
    except KeyError as error:
        return {'result':None,'note':'Syzygy file unavailable; engine play continues. '+str(error)}
