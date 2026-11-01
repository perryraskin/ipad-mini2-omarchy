# Upstream audio review

Reviewed during the persistent J86 audio session:

- [Orchard hardware](https://github.com/OrchardLinux/hardware/tree/824bf0346ae4c3debd208cd34b053130576af60c):
  `docs/bring-up/j71b-audio.md` reports physically confirmed quiet iPad6 left/right
  playback, five starts/stops and touch coexistence. Its shared SmartIO owner,
  bounded DMA queues and NCO reference-clock approach are useful. T8010 MCA-v5,
  MAX98357 bank and channel2 wiring are not J86's MCA-v1/CS35L19/channel1.
- [iPad5 playback reconstruction](https://github.com/brkosebay/omarchy-ipad5/blob/main/docs/audio/playback-path.md):
  useful SmartIO protocol, request-tag handling, clock investigation and IRQ-storm
  lessons. It uses CS42L81 speaker outputs and codec-master clocking, not the
  J86 speaker topology. The newer EP0 SPI region setup does not work on A7;
  the exact firmware model and live rejection establish that difference.
- [Cam's J72](https://github.com/thisiscamk/ipad-air-j72-linux/tree/3fbd8054fe997eb9d020274736b1dc9a2685271a):
  current tree/commits concern Wi-Fi, charging and touch; no audio implementation
  was found in the reviewed tree. This is the closest SoC family, not a speaker
  driver to copy.
- [Project Cascadia](https://github.com/rzxvx/Project-Cascadia/tree/9c175dd):
  fetched latest; newer work includes A13 touch/Wi-Fi. Existing Mini1 CS35L19
  driver informs register protocol but its board records, 32-bit slots and
  clock path cannot replace exact J86 evidence.
- [Omarchy iPhone6s](https://github.com/modpunk/Omarchy-iPhone6s):
  fetched current remote; no new commits beyond the local reference checkout.

Upstream playback claims above belong to those boards. J86 currently has a
live bounded silence-DMA result, with both amps still reset; no audible result.
