// Included inside the experimental module's private namespace.
struct PreparedWeapon {
    uint8_t x, y, width, height;
};

constexpr uint16_t kPreparedWeaponBase = 0x5700u;
constexpr int kFirstPreparedWeapon = 416;
constexpr PreparedWeapon kPreparedWeapons[] = {
#include "weapon_rectangles.inc"
};

int prepared_weapon_index(const WorldMirror &world) {
    const int index = world.view_weapon_shape - kFirstPreparedWeapon;
    return world.hud.palette_shift == 0 && index >= 0 &&
        index < static_cast<int>(sizeof(kPreparedWeapons) / sizeof(kPreparedWeapons[0]))
        ? index : -1;
}

int32_t plot_prepared_weapon(const vdplet_host_v1 *host, unsigned index) {
    const vdplet_host_v1_1 *vdu = vdplet_vdu_host(host);
    if (vdu == nullptr) return VDPL_E_ABI;
    const PreparedWeapon &rect = kPreparedWeapons[index];
    const uint16_t id = kPreparedWeaponBase + index;
    const uint32_t bytes = uint32_t(rect.width) * rect.height;
    vdplet_view_v1 backing = {sizeof(backing), 0, nullptr, 0, 0};
    int32_t status = host->buffer_acquire(host->context, id, VDPL_READ, 0, bytes, &backing);
    if (status != VDPL_OK) return status;
    const bool valid = backing.data != nullptr && backing.bytes >= bytes;
    status = host->buffer_release(host->context, backing.lease);
    if (status != VDPL_OK) return status;
    if (!valid) return VDPL_E_BUFFER;
    const uint8_t plot[] = {23, 27, 32, uint8_t(id), uint8_t(id >> 8),
                            23, 27, 3, rect.x, 0, rect.y, 0};
    return vdu->vdu_submit(host->context, plot, sizeof(plot));
}
