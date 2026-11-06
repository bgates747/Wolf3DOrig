// Included inside the task-owned Wolf3dControl class only. No production ABI.
WolfPerfRecorder wp_recorder;
bool wp_control(VDUStreamProcessor &processor, uint8_t op) {
    const int token=processor.readWord_t(), offset=processor.readWord_t();
    if (token<0 || offset<0) return false;
    uint16_t value=0;
    bool ok=false;
    if (op==240) {
        const auto found=buffers.find(0xf000);
        ok=offset==0 && found!=buffers.end() && found->second.size()==1 &&
            wp_recorder.reset(found->second[0]->getBuffer(),
                              found->second[0]->size(), wp_core());
    } else if (op==241) {
        ok=wp_recorder.read16(uint32_t(offset),value);
    }
    uint8_t packet[10]={'W','3','D','T',1,uint8_t(ok),
                       uint8_t(token),uint8_t(token>>8),
                       uint8_t(value),uint8_t(value>>8)};
    processor.send_packet(PACKET_KEYCODE,sizeof(packet),packet);
    return ok;
}
