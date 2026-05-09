`timescale 1ns/1ps

module tb_sync_fifo;

    localparam DATA_WIDTH = 8;
    localparam ADDR_WIDTH = 2;
    localparam DEPTH      = (1 << ADDR_WIDTH);
    localparam CLK_PERIOD = 10;

    reg                   clk;
    reg                   rst_n;
    reg                   wr_en;
    reg                   rd_en;
    reg  [DATA_WIDTH-1:0] din;
    wire [DATA_WIDTH-1:0] dout;
    wire                  dout_valid;
    wire                  full;
    wire                  empty;
    genvar                mem_idx;

    sync_fifo #(
        .DATA_WIDTH(DATA_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(wr_en),
        .rd_en(rd_en),
        .din(din),
        .dout(dout),
        .dout_valid(dout_valid),
        .full(full),
        .empty(empty)
    );

    generate
        for (mem_idx = 0; mem_idx < DEPTH; mem_idx = mem_idx + 1) begin : g_mem_probe
            wire [DATA_WIDTH-1:0] mem_word = dut.mem[mem_idx];
        end
    endgenerate

    initial begin
        clk = 1'b0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end

    initial begin
`ifdef FSDB
        $fsdbDumpfile("sim/fifo_wave.fsdb");
        $fsdbDumpvars(0, tb_sync_fifo, "+mda");
        $fsdbDumpMDA(0, tb_sync_fifo.dut);
`else
        $dumpfile("sim/fifo_wave.vcd");
        $dumpvars(0, tb_sync_fifo);
`endif
    end

    initial begin
        rst_n = 1'b0;
        wr_en = 1'b0;
        rd_en = 1'b0;
        din   = {DATA_WIDTH{1'b0}};

        repeat (3) @(posedge clk);
        rst_n = 1'b1;
        @(posedge clk);

        $display("[%0t] Write 4 items, FIFO becomes full", $time);
        write_data(8'h11);
        write_data(8'h22);
        write_data(8'h33);
        write_data(8'h44);

        $display("[%0t] Try one extra write while full, data is ignored", $time);
        write_data(8'h55);

        $display("[%0t] Read 2 items, should get 11 then 22", $time);
        read_data();
        read_data();

        $display("[%0t] Write 2 more items to show circular pointer wrap", $time);
        write_data(8'h55);
        write_data(8'h66);

        $display("[%0t] Simultaneous read/write while FIFO is full", $time);
        read_write_same_cycle(8'h77);

        $display("[%0t] Drain FIFO", $time);
        read_data();
        read_data();
        read_data();
        read_data();

        $display("[%0t] Try read while empty", $time);
        read_data();

        repeat (4) @(posedge clk);
        $finish;
    end

    task write_data;
        input [DATA_WIDTH-1:0] data;
        begin
            @(negedge clk);
            wr_en = 1'b1;
            rd_en = 1'b0;
            din   = data;
            @(negedge clk);
            wr_en = 1'b0;
            din   = {DATA_WIDTH{1'b0}};
        end
    endtask

    task read_data;
        begin
            @(negedge clk);
            wr_en = 1'b0;
            rd_en = 1'b1;
            @(negedge clk);
            rd_en = 1'b0;
        end
    endtask

    task read_write_same_cycle;
        input [DATA_WIDTH-1:0] data;
        begin
            @(negedge clk);
            wr_en = 1'b1;
            rd_en = 1'b1;
            din   = data;
            @(negedge clk);
            wr_en = 1'b0;
            rd_en = 1'b0;
            din   = {DATA_WIDTH{1'b0}};
        end
    endtask

    always @(posedge clk) begin
        if (rst_n) begin
            $display("[%0t] wr_en=%0b rd_en=%0b din=%02h dout=%02h valid=%0b full=%0b empty=%0b wr_ptr=%0d rd_ptr=%0d",
                     $time, wr_en, rd_en, din, dout, dout_valid, full, empty, dut.wr_ptr, dut.rd_ptr);
        end
    end

endmodule
