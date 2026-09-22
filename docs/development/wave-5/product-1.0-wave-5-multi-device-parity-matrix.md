# Product 1.0 Wave 5 Multi-device Parity Matrix

| Scenario | Split plan | Merge result | Replay behavior |
|---|---|---|---|
| single device execution | degenerate split | single final artifact | stable |
| multi-device deterministic split | stable shards | deterministic merge | stable |
| partial shard failure | stable retry semantics | terminal failure or recovery | documented |
| backend normalization mismatch | stable rejection | canonical error | stable |
| redelivery after lease expiry | same accepted plan | same final state | stable |
