; =============================================================================

; Authoritative eZ80 actor pool and VDP snapshot bridge.
;
; The pool keeps the original fixed MAXACTORS ownership model while replacing
; near pointers with stable uint8 slot ids. Slot zero is reserved for the
; player; slots 1..149 form live/free lists and map directly to VDP actorId.
; A separate 64x64 actorat grid stores the reserved destination slot, leaving
; walls/doors in the render tilemap and blocking statics in their own bitset.
;
; This production slice seeds and renders the real E1L1 actors. Allocation,
; lifetime, occupancy, dirty submission, and player collision live here; the
; original-timed state/path runner is kept separately in wolf3d_actor_sim.inc.
; =============================================================================

; ---------------------------------------------------------------------------
; Initial state render/timing table
; ---------------------------------------------------------------------------

; record: int16 base shapenum, uint8 rotations (0/2/8), uint16 original
; 70-Hz tictime, uint8 think id, uint8 end-action id, uint8 next-state id.
; The 30-Hz client advances original time with one shared exact 2,2,3-tic
; cadence, retaining the DOS state graph and its initial random phases.
w3d_actor_states:
    dw -1              ; 0 invalid/free
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,0
    dw 50              ; 1 s_grdstand / SPR_GRD_S_1
    db 8
    dw 0
    db W3D_STATE_THINK_STAND,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_STAND
    dw 58              ; 2 s_grdpath1 / SPR_GRD_W1_1
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_PATH1S
    dw 99              ; 3 s_dogpath1 / SPR_DOG_W1_1
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_PATH1S
    dw 238             ; 4 s_ofcstand / SPR_OFC_S_1
    db 8
    dw 0
    db W3D_STATE_THINK_STAND,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_STAND
    dw 246             ; 5 s_ofcpath1 / SPR_OFC_W1_1
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_PATH1S
    dw 187             ; 6 s_mutstand / SPR_MUT_S_1
    db 8
    dw 0
    db W3D_STATE_THINK_STAND,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_STAND
    dw 195             ; 7 s_mutpath1 / SPR_MUT_W1_1
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_PATH1S
    dw 138             ; 8 s_ssstand / SPR_SS_S_1
    db 8
    dw 0
    db W3D_STATE_THINK_STAND,W3D_STATE_ACTION_NONE,W3D_STATE_SS_STAND
    dw 146             ; 9 s_sspath1 / SPR_SS_W1_1
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_SS_PATH1S
    dw 95              ; 10 s_grddie4 / SPR_GRD_DEAD
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_DEAD
    dw 288             ; 11 s_blinkychase1 (AI later)
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_BLINKY_CHASE1
    dw 292             ; 12 s_clydechase1 (AI later)
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_CLYDE_CHASE1
    dw 290             ; 13 s_pinkychase1 (AI later)
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_PINKY_CHASE1
    dw 294             ; 14 s_inkychase1 (AI later)
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_INKY_CHASE1
    dw 296             ; 15 s_bossstand
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_BOSS_STAND
    dw 385             ; 16 s_gretelstand
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRETEL_STAND
    dw 307             ; 17 s_schabbstand
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SCHABBS_STAND
    dw 360             ; 18 s_giftstand
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GIFT_STAND
    dw 396             ; 19 s_fatstand
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_FAT_STAND
    dw 321             ; 20 s_fakestand / SPR_FAKE_W1
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_FAKE_STAND
    dw 334             ; 21 s_mechastand
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MECHA_STAND

; Complete ordinary-enemy path animation chains. The silent W1/W3 pause
; states intentionally retain the same shape as their preceding frame.
    dw 58              ; 22 s_grdpath1s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_PATH2
    dw 66              ; 23 s_grdpath2
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_PATH3
    dw 74              ; 24 s_grdpath3
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_PATH3S
    dw 74              ; 25 s_grdpath3s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_PATH4
    dw 82              ; 26 s_grdpath4
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_PATH1

    dw 99              ; 27 s_dogpath1s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_PATH2
    dw 107             ; 28 s_dogpath2
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_PATH3
    dw 115             ; 29 s_dogpath3
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_PATH3S
    dw 115             ; 30 s_dogpath3s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_PATH4
    dw 123             ; 31 s_dogpath4
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_PATH1

    dw 246             ; 32 s_ofcpath1s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_PATH2
    dw 254             ; 33 s_ofcpath2
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_PATH3
    dw 262             ; 34 s_ofcpath3
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_PATH3S
    dw 262             ; 35 s_ofcpath3s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_PATH4
    dw 270             ; 36 s_ofcpath4
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_PATH1

    dw 195             ; 37 s_mutpath1s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_PATH2
    dw 203             ; 38 s_mutpath2
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_PATH3
    dw 211             ; 39 s_mutpath3
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_PATH3S
    dw 211             ; 40 s_mutpath3s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_PATH4
    dw 219             ; 41 s_mutpath4
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_PATH1

    dw 146             ; 42 s_sspath1s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_PATH2
    dw 154             ; 43 s_sspath2
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_SS_PATH3
    dw 162             ; 44 s_sspath3
    db 8
    dw 20
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_SS_PATH3S
    dw 162             ; 45 s_sspath3s
    db 8
    dw 5
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_PATH4
    dw 170             ; 46 s_sspath4
    db 8
    dw 15
    db W3D_STATE_THINK_PATH,W3D_STATE_ACTION_NONE,W3D_STATE_SS_PATH1

; Stable FirstSighting targets. The remaining five frames of each chain append
; below ids 47..51, preserving the awareness ABI while restoring the original
; W1/W1s/W2/W3/W3s/W4 chase timing.
    dw 58              ; 47 s_grdchase1 / SPR_GRD_W1_1
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE1S
    dw 99              ; 48 s_dogchase1 / SPR_DOG_W1_1
    db 8
    dw 10
    db W3D_STATE_THINK_DOG_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE1S
    dw 246             ; 49 s_ofcchase1 / SPR_OFC_W1_1
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE1S
    dw 195             ; 50 s_mutchase1 / SPR_MUT_W1_1
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE1S
    dw 146             ; 51 s_sschase1 / SPR_SS_W1_1
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE1S

    dw 58              ; 52 s_grdchase1s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE2
    dw 66              ; 53 s_grdchase2
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE3
    dw 74              ; 54 s_grdchase3
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE3S
    dw 74              ; 55 s_grdchase3s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE4
    dw 82              ; 56 s_grdchase4
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE1

    dw 99              ; 57 s_dogchase1s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE2
    dw 107             ; 58 s_dogchase2
    db 8
    dw 8
    db W3D_STATE_THINK_DOG_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE3
    dw 115             ; 59 s_dogchase3
    db 8
    dw 10
    db W3D_STATE_THINK_DOG_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE3S
    dw 115             ; 60 s_dogchase3s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE4
    dw 123             ; 61 s_dogchase4
    db 8
    dw 8
    db W3D_STATE_THINK_DOG_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE1

    dw 246             ; 62 s_ofcchase1s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE2
    dw 254             ; 63 s_ofcchase2
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE3
    dw 262             ; 64 s_ofcchase3
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE3S
    dw 262             ; 65 s_ofcchase3s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE4
    dw 270             ; 66 s_ofcchase4
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE1

    dw 195             ; 67 s_mutchase1s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE2
    dw 203             ; 68 s_mutchase2
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE3
    dw 211             ; 69 s_mutchase3
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE3S
    dw 211             ; 70 s_mutchase3s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE4
    dw 219             ; 71 s_mutchase4
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE1

    dw 146             ; 72 s_sschase1s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE2
    dw 154             ; 73 s_sschase2
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE3
    dw 162             ; 74 s_sschase3
    db 8
    dw 10
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE3S
    dw 162             ; 75 s_sschase3s
    db 8
    dw 3
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE4
    dw 170             ; 76 s_sschase4
    db 8
    dw 8
    db W3D_STATE_THINK_CHASE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE1

; Original ordinary-enemy attack animations. End actions run before NEXT,
; exactly as in DoActor: T_Shoot on the muzzle-flash records and T_Bite on
; dog jump2. These states do not rotate; their art already faces the camera.
    dw 96              ; 77 s_grdshoot1 / SPR_GRD_SHOOT1
    db 0
    dw 20
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_SHOOT2
    dw 97              ; 78 s_grdshoot2 / SPR_GRD_SHOOT2
    db 0
    dw 20
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT,W3D_STATE_GRD_SHOOT3
    dw 98              ; 79 s_grdshoot3 / SPR_GRD_SHOOT3
    db 0
    dw 20
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE1

    dw 135             ; 80 s_dogjump1 / SPR_DOG_JUMP1
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_JUMP2
    dw 136             ; 81 s_dogjump2 / SPR_DOG_JUMP2
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_BITE,W3D_STATE_DOG_JUMP3
    dw 137             ; 82 s_dogjump3 / SPR_DOG_JUMP3
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_JUMP4
    dw 135             ; 83 s_dogjump4 / SPR_DOG_JUMP1
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_JUMP5
    dw 99              ; 84 s_dogjump5 / SPR_DOG_W1_1
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_CHASE1

    dw 285             ; 85 s_ofcshoot1 / SPR_OFC_SHOOT1
    db 0
    dw 6
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_SHOOT2
    dw 286             ; 86 s_ofcshoot2 / SPR_OFC_SHOOT2
    db 0
    dw 20
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT,W3D_STATE_OFC_SHOOT3
    dw 287             ; 87 s_ofcshoot3 / SPR_OFC_SHOOT3
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE1

    dw 234             ; 88 s_mutshoot1 / SPR_MUT_SHOOT1
    db 0
    dw 6
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT,W3D_STATE_MUT_SHOOT2
    dw 235             ; 89 s_mutshoot2 / SPR_MUT_SHOOT2
    db 0
    dw 20
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_SHOOT3
    dw 236             ; 90 s_mutshoot3 / SPR_MUT_SHOOT3
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT,W3D_STATE_MUT_SHOOT4
    dw 237             ; 91 s_mutshoot4 / SPR_MUT_SHOOT4
    db 0
    dw 20
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE1

    dw 184             ; 92 s_ssshoot1 / SPR_SS_SHOOT1
    db 0
    dw 20
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_SHOOT2
    dw 185             ; 93 s_ssshoot2 / SPR_SS_SHOOT2
    db 0
    dw 20
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT,W3D_STATE_SS_SHOOT3
    dw 186             ; 94 s_ssshoot3 / SPR_SS_SHOOT3
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_SHOOT4
    dw 185             ; 95 s_ssshoot4 / SPR_SS_SHOOT2
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT,W3D_STATE_SS_SHOOT5
    dw 186             ; 96 s_ssshoot5 / SPR_SS_SHOOT3
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_SHOOT6
    dw 185             ; 97 s_ssshoot6 / SPR_SS_SHOOT2
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT,W3D_STATE_SS_SHOOT7
    dw 186             ; 98 s_ssshoot7 / SPR_SS_SHOOT3
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_SHOOT8
    dw 185             ; 99 s_ssshoot8 / SPR_SS_SHOOT2
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_SHOOT,W3D_STATE_SS_SHOOT9
    dw 186             ; 100 s_ssshoot9 / SPR_SS_SHOOT3
    db 0
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE1

; Original ordinary-enemy pain and death animations.  Pain records use the
; source's rotate=2 rule.  A_DeathScream is an end action on the first death
; frame; its port-side dispatcher publishes a sound event without making
; audio part of authoritative actor state.
    dw 90              ; 101 s_grdpain / SPR_GRD_PAIN_1
    db 2
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE1
    dw 94              ; 102 s_grdpain1 / SPR_GRD_PAIN_2
    db 2
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_CHASE1
    dw 91              ; 103 s_grddie1 / SPR_GRD_DIE_1
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_DEATH_SCREAM,W3D_STATE_GRD_DIE2
    dw 92              ; 104 s_grddie2 / SPR_GRD_DIE_2
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_DIE3
    dw 93              ; 105 s_grddie3 / SPR_GRD_DIE_3
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_GRD_DEAD

    dw 131             ; 106 s_dogdie1 / SPR_DOG_DIE_1
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_DEATH_SCREAM,W3D_STATE_DOG_DIE2
    dw 132             ; 107 s_dogdie2 / SPR_DOG_DIE_2
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_DIE3
    dw 133             ; 108 s_dogdie3 / SPR_DOG_DIE_3
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_DEAD
    dw 134             ; 109 s_dogdead / SPR_DOG_DEAD
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_DOG_DEAD

    dw 278             ; 110 s_ofcpain / SPR_OFC_PAIN_1
    db 2
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE1
    dw 282             ; 111 s_ofcpain1 / SPR_OFC_PAIN_2
    db 2
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_CHASE1
    dw 279             ; 112 s_ofcdie1 / SPR_OFC_DIE_1
    db 0
    dw 11
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_DEATH_SCREAM,W3D_STATE_OFC_DIE2
    dw 280             ; 113 s_ofcdie2 / SPR_OFC_DIE_2
    db 0
    dw 11
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_DIE3
    dw 281             ; 114 s_ofcdie3 / SPR_OFC_DIE_3
    db 0
    dw 11
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_DIE4
    dw 283             ; 115 s_ofcdie4 / SPR_OFC_DIE_4
    db 0
    dw 11
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_DEAD
    dw 284             ; 116 s_ofcdie5 / SPR_OFC_DEAD
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_OFC_DEAD

    dw 227             ; 117 s_mutpain / SPR_MUT_PAIN_1
    db 2
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE1
    dw 231             ; 118 s_mutpain1 / SPR_MUT_PAIN_2
    db 2
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_CHASE1
    dw 228             ; 119 s_mutdie1 / SPR_MUT_DIE_1
    db 0
    dw 7
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_DEATH_SCREAM,W3D_STATE_MUT_DIE2
    dw 229             ; 120 s_mutdie2 / SPR_MUT_DIE_2
    db 0
    dw 7
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_DIE3
    dw 230             ; 121 s_mutdie3 / SPR_MUT_DIE_3
    db 0
    dw 7
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_DIE4
    dw 232             ; 122 s_mutdie4 / SPR_MUT_DIE_4
    db 0
    dw 7
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_DEAD
    dw 233             ; 123 s_mutdie5 / SPR_MUT_DEAD
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_MUT_DEAD

    dw 178             ; 124 s_sspain / SPR_SS_PAIN_1
    db 2
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE1
    dw 182             ; 125 s_sspain1 / SPR_SS_PAIN_2
    db 2
    dw 10
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_CHASE1
    dw 179             ; 126 s_ssdie1 / SPR_SS_DIE_1
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_DEATH_SCREAM,W3D_STATE_SS_DIE2
    dw 180             ; 127 s_ssdie2 / SPR_SS_DIE_2
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_DIE3
    dw 181             ; 128 s_ssdie3 / SPR_SS_DIE_3
    db 0
    dw 15
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_DEAD
    dw 183             ; 129 s_ssdie4 / SPR_SS_DEAD
    db 0
    dw 0
    db W3D_STATE_THINK_NONE,W3D_STATE_ACTION_NONE,W3D_STATE_SS_DEAD
w3d_actor_states_end:

; ---------------------------------------------------------------------------
; Pool initialization and slot/list primitives
; ---------------------------------------------------------------------------

w3d_initialize_actor_state:
    ld hl,(w3d_level_area_ptr)
    ld (w3d_area_map_ptr),hl
    ld hl,(w3d_level_path_ptr)
    ld (w3d_path_directions_ptr),hl
; Deterministically clear every byte; do not depend on MOS loader BSS policy.
    xor a
    ld hl,w3d_actors
    ld (hl),a
    ld de,w3d_actors+1
    ld bc,W3D_MAX_ACTORS*W3D_ACTOR_SIZE-1
    ldir
    ld hl,w3d_actorat
    ld (hl),a
    ld de,w3d_actorat+1
    ld bc,W3D_MAP_BYTES-1
    ldir
    ld hl,w3d_actor_dirty
    ld (hl),a
    ld de,w3d_actor_dirty+1
    ld bc,W3D_MAX_ACTORS-1
    ldir

; Slot zero is reserved for the player and never enters either list.
    ld ix,w3d_actors
    ld a,W3D_ACTOR_ACTIVE_ALWAYS
    ld (ix+W3D_ACTOR_ACTIVE),a
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld (ix+W3D_ACTOR_PREV),a

; Build the complete 1..149 free chain in PREV. Generated live seeds copied
; below overwrite their PREV/NEXT fields with the row-major live chain.
    ld ix,w3d_actors+W3D_ACTOR_SIZE
    ld a,1
@free_chain:
    ld (w3d_actor_init_slot),a
    ld (ix+W3D_ACTOR_ACTIVE),W3D_ACTOR_ACTIVE_FREE
    ld (ix+W3D_ACTOR_NEXT),W3D_SLOT_NONE
    inc a
    cp W3D_MAX_ACTORS
    jr c,@have_free_successor
    ld a,W3D_SLOT_NONE
@have_free_successor:
    ld (ix+W3D_ACTOR_PREV),a
    ld a,(w3d_actor_init_slot)
    inc a
    lea ix,ix+W3D_ACTOR_SIZE
    cp W3D_MAX_ACTORS
    jr c,@free_chain

; Slot ids in the generated records start at one. They already contain the
; correct original active state, cached destination, and live next/prev links.
    ld a,(w3d_level_actor_count)
    ld (w3d_actor_count),a
    or a
    jr z,@no_live_seed
    ld hl,(w3d_level_actor_seed_ptr)
    ld de,w3d_actors+W3D_ACTOR_SIZE
@copy_live_seed:
    ld bc,W3D_ACTOR_SIZE
    ldir
    dec a
    jr nz,@copy_live_seed

    ld a,1
    ld (w3d_actor_live_head),a
    ld a,(w3d_level_actor_count)
    ld (w3d_actor_live_tail),a
    jr @set_free_head
@no_live_seed:
    ld a,W3D_SLOT_NONE
    ld (w3d_actor_live_head),a
    ld (w3d_actor_live_tail),a
@set_free_head:
    ld a,(w3d_level_actor_count)
    inc a
    cp W3D_MAX_ACTORS
    jr c,@free_head_valid
    ld a,W3D_SLOT_NONE
@free_head_valid:
    ld (w3d_actor_free_head),a

; Rebuild actorat from authoritative cached/reserved tiles.
    ld a,(w3d_actor_live_head)
@occupancy_loop:
    cp W3D_SLOT_NONE
    jr z,@done
    ld (w3d_actor_init_slot),a
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NONMARK|W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@next_occupancy
    ld a,(w3d_actor_init_slot)
    call w3d_actorat_claim
@next_occupancy:
    ld a,(ix+W3D_ACTOR_NEXT)
    jr @occupancy_loop
@done:
    ret

; Compare A with the active runtime door count without borrowing a caller's
; coordinate or pointer registers. Carry is set exactly when A is in range.
w3d_compare_door_index:
    push hl
    ld hl,w3d_level_door_count
    cp (hl)
    pop hl
    ret

; A=slot -> IX=record. Destroys DE,HL; A preserved.
w3d_actor_pointer_from_id:
    push af
    ld d,a
    ld e,W3D_ACTOR_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_actors
    add hl,de
    push hl
    pop ix
    pop af
    ret

; A=state id -> IY=state. Invalid/high-byte ids resolve to state zero.
w3d_actor_state_pointer_from_id:
    cp W3D_STATE_COUNT
    jr c,@valid
    xor a
@valid:
    ld d,a
    ld e,W3D_STATE_SIZE
    mlt de
    inc de
    dec.s de
    ld hl,w3d_actor_states
    add hl,de
    push hl
    pop iy
    ret

; Allocate one detached zeroed slot. Carry set on success with A=slot and
; IX=record; carry clear when full. Call w3d_actor_publish after initializing.
w3d_actor_alloc:
    ld a,(w3d_actor_free_head)
    cp W3D_SLOT_NONE
    jr nz,@available
    or a                            ; clear carry
    ret
@available:
    ld (w3d_actor_selected),a
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_PREV)
    ld (w3d_actor_free_head),a
    push ix
    pop hl
    xor a
    ld (hl),a
    ld de,0
    push ix
    pop de
    inc de
    ld bc,W3D_ACTOR_SIZE-1
    ldir
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld (ix+W3D_ACTOR_PREV),a
    ld a,(w3d_actor_selected)
    scf
    ret

; Publish initialized detached slot A/IX at the live tail, claim its cached
; destination when markable, and queue a complete VDP set snapshot.
w3d_actor_publish:
    ld (w3d_actor_selected),a
    ld a,W3D_SLOT_NONE
    ld (ix+W3D_ACTOR_NEXT),a
    ld a,(w3d_actor_live_tail)
    ld (ix+W3D_ACTOR_PREV),a
    cp W3D_SLOT_NONE
    jr z,@first
    call w3d_actor_pointer_from_id
    ld a,(w3d_actor_selected)
    ld (ix+W3D_ACTOR_NEXT),a
    jr @tail_linked
@first:
    ld a,(w3d_actor_selected)
    ld (w3d_actor_live_head),a
@tail_linked:
    ld a,(w3d_actor_selected)
    ld (w3d_actor_live_tail),a
    ld hl,w3d_actor_count
    inc (hl)
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_NONMARK|W3D_ACTOR_FLAG_NEVERMARK
    jr nz,@dirty
    ld a,(w3d_actor_selected)
    call w3d_actorat_claim
@dirty:
    ld a,(w3d_actor_selected)
    jp w3d_actor_mark_dirty

; Remove live slot A/IX. NEXT deliberately remains intact so an actor may
; remove itself during list traversal without losing the following actor.
w3d_actor_free:
    ld (w3d_actor_selected),a
    call w3d_actorat_release
    ld a,(ix+W3D_ACTOR_NEXT)
    ld (w3d_actor_saved_next),a
    ld a,(ix+W3D_ACTOR_PREV)
    ld (w3d_actor_saved_prev),a
    cp W3D_SLOT_NONE
    jr z,@remove_head
    call w3d_actor_pointer_from_id
    ld a,(w3d_actor_saved_next)
    ld (ix+W3D_ACTOR_NEXT),a
    jr @forward_unlinked
@remove_head:
    ld a,(w3d_actor_saved_next)
    ld (w3d_actor_live_head),a
@forward_unlinked:
    ld a,(w3d_actor_saved_next)
    cp W3D_SLOT_NONE
    jr z,@remove_tail
    call w3d_actor_pointer_from_id
    ld a,(w3d_actor_saved_prev)
    ld (ix+W3D_ACTOR_PREV),a
    jr @back_unlinked
@remove_tail:
    ld a,(w3d_actor_saved_prev)
    ld (w3d_actor_live_tail),a
@back_unlinked:
    ld a,(w3d_actor_selected)
    call w3d_actor_pointer_from_id
    ld a,(w3d_actor_free_head)
    ld (ix+W3D_ACTOR_PREV),a
    ld a,W3D_ACTOR_ACTIVE_FREE
    ld (ix+W3D_ACTOR_ACTIVE),a
    xor a
    ld (ix+W3D_ACTOR_STATE+0),a
    ld (ix+W3D_ACTOR_STATE+1),a
    ld a,(w3d_actor_selected)
    ld (w3d_actor_free_head),a
    ld hl,w3d_actor_count
    dec (hl)
    ld a,(w3d_actor_selected)
    call w3d_actor_dirty_address
    ld (hl),W3D_ACTOR_DIRTY_REMOVE
    ld a,1
    ld (w3d_world_dirty),a
    ld a,(w3d_actor_saved_next)
    ret

; A=slot, IX=record: claim cached tile with slot id.
w3d_actorat_claim:
    ld b,a
    call w3d_actorat_address_from_ix
    ld (hl),b
    ret

; A=slot, IX=record: clear cached tile iff it still names this slot.
w3d_actorat_release:
    ld b,a
    call w3d_actorat_address_from_ix
    ld a,(hl)
    cp b
    ret nz
    xor a
    ld (hl),a
    ret

; IX=actor -> HL=&actorat[tiley*64+tilex].
w3d_actorat_address_from_ix:
    ld hl,0
    ld l,(ix+W3D_ACTOR_TILEY)
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,0
    ld e,(ix+W3D_ACTOR_TILEX)
    add.s hl,de
    ld de,w3d_actorat
    add hl,de
    ret

; B=x,C=y -> A=slot or zero. B,C preserved.
w3d_actorat_get:
    push bc
    ld hl,0
    ld l,c
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    add.s hl,hl
    ld de,0
    ld e,b
    add.s hl,de
    ld de,w3d_actorat
    add hl,de
    ld a,(hl)
    pop bc
    ret

; A=slot -> dirty byte address HL.
w3d_actor_dirty_address:
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_actor_dirty
    add hl,de
    ret

w3d_actor_mark_dirty:
    call w3d_actor_dirty_address
    ld (hl),W3D_ACTOR_DIRTY_SET
    ld a,1
    ld (w3d_world_dirty),a
    ret

; ---------------------------------------------------------------------------
; Original player-vs-shootable-actor collision
; ---------------------------------------------------------------------------

; IX -> candidate player position. Return A=1 clear, A=0 blocked. Expand the
; already-computed player AABB tile bounds by one exactly like TryMove (a 3x3
; or 4x4 actorat search); final center deltas use inclusive
; +/-W3D_PHYSICAL_OBJECT_CLEARANCE on both axes.
w3d_player_actors_clear:
    push bc
    push de
    push hl
    push ix
    push iy
    push ix
    pop iy

    ld a,(w3d_clip_x_low)
    or a
    jr z,@x_low_zero
    dec a
@x_low_zero:
    ld (w3d_actor_scan_x_low),a
    ld a,(w3d_clip_x_high)
    cp W3D_MAP_SIZE-1
    jr nc,@x_high_edge
    inc a
@x_high_edge:
    ld (w3d_actor_scan_x_high),a
    ld a,(w3d_clip_y_low)
    or a
    jr z,@y_low_zero
    dec a
@y_low_zero:
    ld (w3d_actor_scan_y),a
    ld a,(w3d_clip_y_high)
    cp W3D_MAP_SIZE-1
    jr nc,@y_high_edge
    inc a
@y_high_edge:
    ld (w3d_actor_scan_y_high),a

@row:
    ld a,(w3d_actor_scan_x_low)
    ld (w3d_actor_scan_x),a
@column:
    ld b,a
    ld a,(w3d_actor_scan_y)
    ld c,a
    call w3d_actorat_get
    or a
    jr z,@next_column
    cp W3D_MAX_ACTORS
    jr nc,@blocked                  ; corrupt occupancy fails closed
    call w3d_actor_pointer_from_id
    ld a,(ix+W3D_ACTOR_FLAGS)
    and W3D_ACTOR_FLAG_SHOOTABLE
    jr z,@next_column

; Absolute 24-bit X delta must exceed the tuned center-spacing threshold.
    ld hl,(iy+0)
    ld de,(ix+W3D_ACTOR_X)
    or a
    sbc hl,de
    jr nc,@x_positive
    ld hl,(ix+W3D_ACTOR_X)
    ld de,(iy+0)
    or a
    sbc hl,de
@x_positive:
    ld de,W3D_PHYSICAL_OBJECT_CLEARANCE+1
    or a
    sbc hl,de
    jr nc,@next_column

; Absolute Y follows the same inclusive threshold.
    ld hl,(iy+4)
    ld de,(ix+W3D_ACTOR_Y)
    or a
    sbc hl,de
    jr nc,@y_positive
    ld hl,(ix+W3D_ACTOR_Y)
    ld de,(iy+4)
    or a
    sbc hl,de
@y_positive:
    ld de,W3D_PHYSICAL_OBJECT_CLEARANCE+1
    or a
    sbc hl,de
    jr c,@blocked

@next_column:
    ld a,(w3d_actor_scan_x)
    ld b,a
    ld a,(w3d_actor_scan_x_high)
    cp b
    jr z,@next_row
    ld a,b
    inc a
    ld (w3d_actor_scan_x),a
    jr @column
@next_row:
    ld a,(w3d_actor_scan_y)
    ld b,a
    ld a,(w3d_actor_scan_y_high)
    cp b
    jr z,@clear
    ld a,b
    inc a
    ld (w3d_actor_scan_y),a
    jp @row

@blocked:
    xor a
    jr @return
@clear:
    ld a,1
@return:
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    ret

; ---------------------------------------------------------------------------
; Dirty actor -> durable VDP render snapshot
; ---------------------------------------------------------------------------

; Called once inside w3d_submit_dirty_world_render. Dirty removals use
; subcommand 5; complete sets use the 15-byte subcommand-4 render contract.
w3d_submit_dirty_actors:
    ld a,1
    ld (w3d_actor_submit_id),a
@loop:
    ld a,(w3d_actor_submit_id)
    cp W3D_MAX_ACTORS
    ret nc
    call w3d_actor_dirty_address
    ld a,(hl)
    cp W3D_ACTOR_DIRTY_REMOVE
    jr z,@remove
    cp W3D_ACTOR_DIRTY_SET
    jr z,@set
@next:
    ld a,(w3d_actor_submit_id)
    inc a
    ld (w3d_actor_submit_id),a
    jr @loop

@remove:
    ld a,(w3d_actor_submit_id)
    ld (w3d_actor_remove_id+0),a
    xor a
    ld (w3d_actor_remove_id+1),a
    ld hl,w3d_actor_remove_command
    ld bc,w3d_actor_remove_end-w3d_actor_remove_command
    rst.lil 18h
    jp @clear_dirty

@set:
    ld a,(w3d_actor_submit_id)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_ID+0),a
    xor a
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_ID+1),a
    ld a,(w3d_actor_submit_id)
    call w3d_actor_pointer_from_id

; Resolve state render metadata. A high state byte or out-of-range low byte
; maps to invalid state zero. Shape -1 retains the original temp1 override.
    ld a,(ix+W3D_ACTOR_STATE+1)
    or a
    jr nz,@invalid_state
    ld a,(ix+W3D_ACTOR_STATE+0)
    jr @state_id_ready
@invalid_state:
    xor a
@state_id_ready:
    call w3d_actor_state_pointer_from_id
    ld a,(iy+W3D_STATE_SHAPENUM+0)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_SHAPENUM+0),a
    ld b,a
    ld a,(iy+W3D_STATE_SHAPENUM+1)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_SHAPENUM+1),a
    and b
    inc a
    jr nz,@shape_ready
    ld a,(ix+W3D_ACTOR_TEMP1+0)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_SHAPENUM+0),a
    ld a,(ix+W3D_ACTOR_TEMP1+1)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_SHAPENUM+1),a
@shape_ready:
    ld a,(iy+W3D_STATE_ROTATIONS)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_ROTATIONS),a

; x/y form the authoritative record prefix, so one eight-byte copy suffices.
    push ix
    pop hl
    ld de,w3d_actor_wire_record+W3D_ACTOR_WIRE_X
    ld bc,8
    ldir

; Ordinary direction is exact 45-degree octants. NODIR entities use their
; continuous actor angle (projectiles in the later combat slice).
    ld a,(ix+W3D_ACTOR_DIR)
    cp W3D_DIR_NODIR
    jr nc,@continuous_facing
    add a,a
    ld e,a
    ld d,0
    inc de
    dec.s de
    ld hl,w3d_actor_direction_degrees
    add hl,de
    ld a,(hl)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_FACING+0),a
    inc hl
    ld a,(hl)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_FACING+1),a
    jr @send_set
@continuous_facing:
    ld a,(ix+W3D_ACTOR_ANGLE+0)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_FACING+0),a
    ld a,(ix+W3D_ACTOR_ANGLE+1)
    ld (w3d_actor_wire_record+W3D_ACTOR_WIRE_FACING+1),a
@send_set:
    ld hl,w3d_actor_set_command
    ld bc,w3d_actor_set_end-w3d_actor_set_command
    rst.lil 18h

@clear_dirty:
    ld a,(w3d_actor_submit_id)
    call w3d_actor_dirty_address
    xor a
    ld (hl),a
    jp @next

w3d_actor_direction_degrees:
    dw 0,45,90,135,180,225,270,315

w3d_actor_set_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,4
w3d_actor_wire_record:
    ds W3D_ACTOR_WIRE_SIZE
w3d_actor_set_end:

w3d_actor_remove_command:
    db 23,0,0A0h
    dw W3D_FIXTURE_CONTROL_BUFFER_ID
    db 4Ah,5
w3d_actor_remove_id:
    dw 0
w3d_actor_remove_end:

; ---------------------------------------------------------------------------
; Storage
; ---------------------------------------------------------------------------

; Loader-facing mutable level bindings. The generated E1L1 fixture remains
; the default so every standalone regression harness retains its deterministic
; seed without needing to include the production package loader.
w3d_level_player_seed_ptr:
    dl w3d_fixture_initial_player_pose
w3d_level_door_seed_ptr:
    dl w3d_fixture_initial_doors
w3d_level_static_seed_ptr:
    dl w3d_fixture_initial_statics
w3d_level_actor_seed_ptr:
    dl w3d_fixture_initial_actors
w3d_level_blocking_ptr:
    dl w3d_fixture_static_blocking_bits
w3d_level_area_ptr:
    dl w3d_fixture_area_map
w3d_level_path_ptr:
    dl w3d_fixture_path_directions
w3d_level_tilemap_ptr:
    dl w3d_fixture_tilemap
w3d_level_door_count:
    db W3D_FIXTURE_DOOR_COUNT
w3d_level_static_count:
    dw W3D_FIXTURE_STATIC_COUNT
w3d_level_actor_count:
    db W3D_FIXTURE_ACTOR_COUNT
w3d_level_random_index:
    db W3D_FIXTURE_RND_INDEX_AFTER_SPAWN

w3d_actors:
    ds W3D_MAX_ACTORS*W3D_ACTOR_SIZE

w3d_actorat:
    ds W3D_MAP_BYTES

w3d_actor_dirty:
    ds W3D_MAX_ACTORS

w3d_area_map_ptr:
    dl 0
w3d_path_directions_ptr:
    dl 0

w3d_actor_free_head:
    db W3D_SLOT_NONE
w3d_actor_live_head:
    db W3D_SLOT_NONE
w3d_actor_live_tail:
    db W3D_SLOT_NONE
w3d_actor_count:
    db 0
w3d_current_actor_index:
    db W3D_SLOT_NONE

w3d_actor_selected:
    db W3D_SLOT_NONE
w3d_actor_saved_next:
    db W3D_SLOT_NONE
w3d_actor_saved_prev:
    db W3D_SLOT_NONE
w3d_actor_init_slot:
    db 0
w3d_actor_submit_id:
    db 0
w3d_actor_scan_x_low:
    db 0
w3d_actor_scan_x_high:
    db 0
w3d_actor_scan_x:
    db 0
w3d_actor_scan_y:
    db 0
w3d_actor_scan_y_high:
    db 0
