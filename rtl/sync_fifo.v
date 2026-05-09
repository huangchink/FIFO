`timescale 1ns/1ps

module sync_fifo #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 3
) (
    input                       clk,
    input                       rst_n,
    input                       wr_en,
    input                       rd_en,
    input  [DATA_WIDTH-1:0]     din,
    output reg [DATA_WIDTH-1:0] dout,
    output reg                  dout_valid,
    output                      full,
    output                      empty
);

    localparam DEPTH = (1 << ADDR_WIDTH);

    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    reg [ADDR_WIDTH:0] wr_ptr;
    reg [ADDR_WIDTH:0] rd_ptr;

    wire rd_fire;
    wire wr_fire;

    assign empty = (wr_ptr == rd_ptr);
    assign full  = (wr_ptr[ADDR_WIDTH]     != rd_ptr[ADDR_WIDTH]) &&
                   (wr_ptr[ADDR_WIDTH-1:0] == rd_ptr[ADDR_WIDTH-1:0]);

    assign rd_fire = rd_en && !empty;
    assign wr_fire = wr_en && (!full || rd_fire);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr     <= {(ADDR_WIDTH+1){1'b0}};
            rd_ptr     <= {(ADDR_WIDTH+1){1'b0}};
            dout       <= {DATA_WIDTH{1'b0}};
            dout_valid <= 1'b0;
        end else begin
            dout_valid <= rd_fire;

            if (wr_fire) begin
                mem[wr_ptr[ADDR_WIDTH-1:0]] <= din;
                wr_ptr <= wr_ptr + 1'b1;
            end

            if (rd_fire) begin
                dout <= mem[rd_ptr[ADDR_WIDTH-1:0]];
                rd_ptr <= rd_ptr + 1'b1;
            end
        end
    end

endmodule
