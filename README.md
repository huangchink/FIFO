# Sync FIFO in Verilog

這個範例是一個單時脈同步 FIFO，使用 read/write pointer 的 wrap bit 判斷 `full` / `empty`，不使用 occupancy counter。

## 檔案

- `rtl/sync_fifo.v`: FIFO RTL
- `tb/tb_sync_fifo.v`: testbench
- `sim/fifo_wave.vcd`: 模擬後產生的波形檔

## 模擬

```powershell
iverilog -o sim/fifo_tb.vvp rtl/sync_fifo.v tb/tb_sync_fifo.v
vvp sim/fifo_tb.vvp
```

## 無 Counter FIFO 原理

這版 FIFO 不使用 `count`。`wr_ptr` 和 `rd_ptr` 都是 `ADDR_WIDTH+1` bit：

```verilog
reg [ADDR_WIDTH:0] wr_ptr;
reg [ADDR_WIDTH:0] rd_ptr;
```

低位元是 memory address，高位元是 wrap bit：

```text
ptr[ADDR_WIDTH-1:0] = memory address
ptr[ADDR_WIDTH]     = wrap bit
```

狀態判斷：

```verilog
assign empty = (wr_ptr == rd_ptr);
assign full  = (wr_ptr[ADDR_WIDTH]     != rd_ptr[ADDR_WIDTH]) &&
               (wr_ptr[ADDR_WIDTH-1:0] == rd_ptr[ADDR_WIDTH-1:0]);
```

也就是：

- `empty`: 兩個 pointer 完全一樣。
- `full`: address 一樣，但 wrap bit 不一樣。

## FSDB 模擬

FSDB 需要 VCS、Xcelium、Questa 這類有連到 Verdi/Novas FSDB dumper 的 simulator；Icarus Verilog 只能產生 VCD。

testbench 裡已經加了條件編譯：

```verilog
`ifdef FSDB
    $fsdbDumpfile("sim/fifo_wave.fsdb");
    $fsdbDumpvars(0, tb_sync_fifo, "+mda");
    $fsdbDumpMDA(0, tb_sync_fifo.dut);
`endif
```

VCS 範例：

```sh
vcs -full64 -sverilog +vpi +memcbk +vcsd +define+FSDB \
    rtl/sync_fifo.v tb/tb_sync_fifo.v \
    -o sim/fifo_simv
./sim/fifo_simv
verdi -ssf sim/fifo_wave.fsdb
```

## 看波形

用 GTKWave 或其他 VCD viewer 開啟：

```powershell
gtkwave sim/fifo_wave.vcd
```

如果沒有 GTKWave，也可以把 `sim/fifo_wave.vcd` 上傳到 EPWave 或用 VS Code 的 waveform extension 查看。

本專案也提供不用安裝 GTKWave 的 SVG 波形圖：

```powershell
python tools/vcd_to_svg.py sim/fifo_wave.vcd sim/fifo_wave.svg
```

產生後直接用瀏覽器或 VS Code 開啟：

```text
sim/fifo_wave.svg
```

## 建議觀察的訊號

- `clk`, `rst_n`: clock 與 reset
- `wr_en`, `din`: 寫入控制與寫入資料
- `rd_en`, `dout`, `dout_valid`: 讀出控制、讀出資料與有效旗標
- `full`, `empty`: FIFO 狀態
- `dut.wr_ptr`, `dut.rd_ptr`: 觀察 pointer address 與 wrap bit
- FSDB: `tb_sync_fifo.dut.mem`
- VCD: `tb_sync_fifo.g_mem_probe[*].mem_word`

## 測試流程

1. 寫入 `11`, `22`, `33`, `44`，FIFO 變滿。
2. FIFO 滿時嘗試寫入 `55`，會被忽略。
3. 讀出兩筆，順序會是 `11`, `22`。
4. 再寫入 `55`, `66`，可以看到 pointer wrap around。
5. FIFO 滿時同一拍 read/write，讀出舊資料，同時寫入 `77`。
6. 最後清空 FIFO，讀出順序維持先進先出。
