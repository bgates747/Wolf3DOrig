RenderDetail cast_walls(const WorldMirror &world, const uint8_t *map,
                        int32_t *heights, uint8_t *tiles, uint8_t *tex_u,
                        uint8_t *sides, const ViewState &view) {
    const int32_t fine_view = static_cast<int32_t>(world.player.angle) * 10;
    for (int col=0;col<kViewWidth;++col) {
        const int fine=normalize_fine(fine_view+kWolfPixelAngleFine[col]);
        const auto tile=[&](int x,int y) {return tile_at(world,map,x,y);};
        const original_raywalk::Hit hit=original_raywalk::trace(world,tile,fine,view.x,view.y);
        if (!hit.valid) return RenderDetail::world;
        if (!hit.found) {heights[col]=0;tiles[col]=tex_u[col]=sides[col]=0;continue;}
        heights[col]=projected_height(hit.x,hit.y,view);
        uint8_t value=hit.tile;
        // Bind original adjacent-door wall flags to this port's immutable map
        // and one-bank texture IDs, without changing its wire/asset format.
        if (!hit.moving && value<=0x7f) {
            const int previous_x=hit.map_x-(hit.side==0 ? hit.step_x : 0);
            const int previous_y=hit.map_y-(hit.side==1 ? hit.step_y : 0);
            const uint8_t previous=tile_at(world,map,previous_x,previous_y);
            if (previous>=kDoorFlag && previous<=kDoorMax) {
                const uint8_t index=previous&kDoorMask;
                if (index>=world.door_count) return RenderDetail::world;
                const Door &door=world.doors[index];
                if ((hit.side==1 && door.vertical!=0) || (hit.side==0 && door.vertical==0))
                    value=kDoorJambTexture;
            }
        }
        tiles[col]=value;sides[col]=hit.side;tex_u[col]=hit.u;
    }
    return RenderDetail::ok;
}
