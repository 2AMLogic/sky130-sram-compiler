"""cocotb bench for sram_ctrl (T1 item 9, digital partition).

Runs unchanged against the control RTL and the synthesized gate-level netlist
(see run.py). Checks, against the behavioural model sram_behav and the strobe
protocol documented in rtl/README.md:
  - reset state, 4-phase order and the 4-cycle access latency
  - read-after-write over a directed address walk and a seeded random mix
  - ce ignored while ready=0
  - async reset in the middle of an access
"""
import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

WORDS = int(os.environ.get("SRAM_WORDS", "256"))
BITS = int(os.environ.get("SRAM_BITS", "32"))
MASK = (1 << BITS) - 1
SEED = int(os.environ.get("SRAM_SEED", "20261027"))


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.ce.value = 0
    dut.we.value = 0
    dut.addr.value = 0
    dut.din.value = 0
    await Timer(23, unit="ns")
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


def strobes(dut):
    return (int(dut.pch.value), int(dut.wl_en.value), int(dut.sae.value), int(dut.wen.value))


async def access(dut, we, addr, din=0, check_phases=True):
    """Issue one access at a falling edge and walk its four cycles. Returns dout."""
    while not int(dut.ready.value):
        await FallingEdge(dut.clk)
    dut.ce.value = 1
    dut.we.value = we
    dut.addr.value = addr
    dut.din.value = din
    await RisingEdge(dut.clk)          # accepted here
    await Timer(1, unit="ns")
    dut.ce.value = 0
    dut.we.value = 0
    if check_phases:
        assert not int(dut.ready.value), "ready must drop on acceptance"
        assert strobes(dut) == (0, 1, 0, we), f"WL phase strobes {strobes(dut)}"
        assert int(dut.addr_q.value) == addr and (not we or int(dut.din_q.value) == din)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    if check_phases:
        assert strobes(dut) == (0, 1, 1 - we, we), f"EVAL phase strobes {strobes(dut)}"
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    if check_phases:
        assert strobes(dut) == (1, 0, 0, 0), f"REST phase strobes {strobes(dut)}"
        assert not int(dut.ready.value)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.ready.value), "ready must be back after the REST phase"
    assert strobes(dut) == (1, 0, 0, 0)
    await FallingEdge(dut.clk)
    return int(dut.dout.value)


@cocotb.test()
async def reset_state(dut):
    await start(dut)
    assert int(dut.ready.value) == 1
    assert strobes(dut) == (1, 0, 0, 0)
    assert int(dut.dout.value) == 0


@cocotb.test()
async def write_read_walk(dut):
    """Write a distinct word to every 7th address plus the corners, read all back against the model."""
    await start(dut)
    addrs = sorted(set(list(range(0, WORDS, 7)) + [0, 1, WORDS - 2, WORDS - 1]))
    data = {a: ((a * 0x9E3779B1) ^ 0x5A5A5A5A) & MASK for a in addrs}
    for a in addrs:
        await access(dut, 1, a, data[a])
    for a in addrs:
        got = await access(dut, 0, a)
        assert got == data[a], f"addr {a}: dout {got:#x} != written {data[a]:#x}"
        assert got == int(dut.ref_dout.value), f"addr {a}: controller dout != sram_behav dout"


@cocotb.test()
async def random_mix_vs_model(dut):
    """Seeded random reads/writes; every read checked against sram_behav and a Python dict."""
    await start(dut)
    rng = random.Random(SEED)
    shadow = {}
    for a in range(WORDS):          # define the whole array so reads are never X
        shadow[a] = rng.getrandbits(BITS)
        await access(dut, 1, a, shadow[a], check_phases=False)
    for _ in range(400):
        a = rng.randrange(WORDS)
        if rng.random() < 0.5:
            d = rng.getrandbits(BITS)
            await access(dut, 1, a, d, check_phases=False)
            shadow[a] = d
        else:
            got = await access(dut, 0, a, check_phases=False)
            assert got == shadow[a], f"addr {a}: {got:#x} != {shadow[a]:#x}"
            assert got == int(dut.ref_dout.value), f"addr {a}: controller dout != sram_behav dout"


@cocotb.test()
async def ce_ignored_while_busy(dut):
    """A second ce during the access must not restart it or change the latched address/data."""
    await start(dut)
    await access(dut, 1, 5, 0x12345678 & MASK)
    dut.ce.value = 1
    dut.we.value = 1
    dut.addr.value = 9
    dut.din.value = 0xFFFFFFFF & MASK
    await RisingEdge(dut.clk)          # accepted (access to addr 9 -> write)
    await FallingEdge(dut.clk)
    for _ in range(3):                 # ce stays asserted while busy, different payload each cycle
        dut.addr.value = 11
        dut.din.value = 0
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        if not int(dut.ready.value):
            assert int(dut.addr_q.value) == 9 and int(dut.din_q.value) == (0xFFFFFFFF & MASK)
        await FallingEdge(dut.clk)
    dut.ce.value = 0
    while not int(dut.ready.value):
        await FallingEdge(dut.clk)
    assert await access(dut, 0, 9) == (0xFFFFFFFF & MASK)
    assert await access(dut, 0, 5) == (0x12345678 & MASK)


@cocotb.test()
async def reset_mid_access(dut):
    """Async reset during the WL phase returns every strobe to idle and clears dout."""
    await start(dut)
    await access(dut, 1, 3, 0xA5A5A5A5 & MASK)
    dut.ce.value = 1
    dut.we.value = 1
    dut.addr.value = 3
    dut.din.value = 0x0F0F0F0F & MASK
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.ce.value = 0
    assert strobes(dut)[1] == 1
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    assert strobes(dut) == (1, 0, 0, 0) and int(dut.ready.value) == 1
    assert int(dut.dout.value) == 0
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    assert await access(dut, 0, 3) == (0xA5A5A5A5 & MASK), "an aborted write must not corrupt the earlier word"
