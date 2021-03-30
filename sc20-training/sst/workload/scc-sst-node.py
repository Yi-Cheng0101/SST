import sst
import ConfigParser, argparse
import sys

############################################################################################################################
# Architecture description
# This configuration models a mesh architecture as follows. C = core, M = Memory, X = empty (router only)
#
#   22 cores            22 cores                24 cores            24 cores
#   6 memory channels   8 channels              6 channels          8 channels
#      M   M                M   M                   M   M               M   M
#    C C C C C            C C C C C               C C C C C           C C C C C
#    C C C C C          M C C C C C M             C C C C C         M C C C C C M
#  M C C C C C M          C C C C C             M C C C C C M         C C C C C
#    C C C C C          M C C C C C M             C C C C C         M C C C C C M
#    C C X X X            C C X X X               C C C C X           C C C C X
#      M   M                M   M                   M   M               M   M
#
#   30 cores            30 cores                36 cores            36 cores
#   6 channels          8 channels              6 channels          8 channels
#       M   M               M   M                     M M                 M M
#     C C C C C           C C C C C               C C C C C C         C C C C C C
#     C C C C C           C C C C C               C C C C C C         C C C C C C
#     C C C C C M       M C C C C C M             C C C C C C M     M C C C C C C M
#   M C C C C C         M C C C C C M           M C C C C C C       M C C C C C C M
#     C C C C C           C C C C C               C C C C C C         C C C C C C
#     C C C C C           C C C C C               C C C C C C         C C C C C C
#       M   M               M   M                     M M                 M M
#
#   40 cores            40 cores
#   6 channels          8 channels
#         M M                 M M
#     C C C C C C         C C C C C C
#     C C C C C C         C C C C C C
#     C C C C C C       M C C C C C C M
#   M C C C C C C M       C C C C C C
#     C C C C C C       M C C C C C C M
#     C C C C C C         C C C C C C
#     C C C C X X         C C C C X X
#         M M                 M M
#
# At each populated mesh stop (core - "C" above), there is one core, one L1, one L2 slice, and one L3 slice. 
# The L3 is shared, the L2 is shared or private depending on the configuration option (-s).
# Mesh stops with a memory hanging off them have a memory controller
#
############################################################################################################################


# Options
parser = argparse.ArgumentParser()
parser.add_argument("-n", "--corecount", help="Number of cores: 22, 24, 30, 32, 36, 40", default="22")
parser.add_argument("-c", "--coretype", help="Type of cores: slow, medium, fast", default="slow")
parser.add_argument("-t", "--smt", help="simultaneous multithreading (SMT) or not: no, yes", default="no")
parser.add_argument("-l1", "--l1size", help="L1 size: small, big", default="small")
parser.add_argument("-l2", "--l2size", help="L2 size: small, big", default="small")
parser.add_argument("-s", "--l2type", help="L2 type: private, shared", default="private")
parser.add_argument("-l3", "--l3size", help="L3 size: small, big", default="small")
parser.add_argument("-w", "--memchannels", help="Number of memory channels: 6, 8", default="6")
parser.add_argument("-b", "--noc", help="Network-on-chip frequency: slow, fast", default="slow")
parser.add_argument("-m", "--memtype", help="Memory type: basic, bw, lat", default="basic")
args = parser.parse_args()

# Configurable by user
# Total cost = MemCost + NetCost + Cores * (L1Cost + L2Cost + L3Cost)   => Cores is NOT configurable given a selection of each component cost (must be maximized)
coretype = args.coretype    # slow, medium, fast
smtarg = args.smt           # yes, no
l1size = args.l1size        # big, small
l2type = args.l2type        # private, shared
l2size = args.l2size        # big, small
l3size = args.l3size        # big, small
meshtype = args.noc         # fast, slow
memchan = int(args.memchannels)  # 6, 8
memtype = args.memtype      # basic, bw, lat
corecount = int(args.corecount)  # 22, 24, 30, 32, 36, 40

debugL2 = 0
debugL3 = 0
debugLev = 10

# Error check core count
if not (corecount == 22 or corecount == 24 or corecount == 30 or corecount == 32 or corecount == 36 or corecount == 40):
    print "Error: bad corecount"
    sys.exit(0)

# Compute cost and error check input arguments
per_core_cost = 0

if coretype == "slow":
    per_core_cost = 15
elif coretype == "medium":
    per_core_cost = 23
elif coretype == "fast":
    per_core_cost = 40
else:
    print "Error: bad coretype"
    sys.exit(0)

if smtarg == "yes":
    per_core_cost = per_core_cost * 1.7
elif smtarg != "no":
    print "Error: bad simultaneous multithreading (SMT) type"
    sys.exit(0)

if l1size == "small":
    per_core_cost = per_core_cost + 18
elif l1size == "big":
    per_core_cost = per_core_cost + 28
else:
    print "Error bad l1size"
    sys.exit(0)
    
if l2type == "private" and l2size == "small":
    per_core_cost = per_core_cost + 14
elif l2type == "private" and l2size == "big":
    per_core_cost = per_core_cost + 20
elif l2type == "shared" and l2size == "small":
    per_core_cost = per_core_cost + 16
elif l2type == "shared" and l2size == "big":
    per_core_cost = per_core_cost + 22
else:
    print "Error bad l2type and/or l2size"
    sys.exit(0)

if l3size == "small":
    per_core_cost = per_core_cost + 20
elif l3size == "big":
    per_core_cost = per_core_cost + 24
else:
    print "Error: bad l3size"
    sys.exit(0)

if meshtype == "slow":
    per_core_cost = per_core_cost + 5
elif meshtype == "fast":
    per_core_cost = per_core_cost + 9
else:
    print "Error: bad meshtype"
    sys.exit(0)

if memchan != 6 and memchan != 8:
    print "Error: bad memchan"
    sys.exit(0)

memory_cost = 110 * memchan
if memtype == "bw":
    memory_cost = 200 * memchan
elif memtype == "lat":
    memory_cost = 260 * memchan
elif memtype != "basic":
    print "Error: bad memory type"
    sys.exit(0)

cost = memory_cost + per_core_cost * corecount

print "Configured with:"
print "  corecount:    " + str(corecount)
print "  coretype:     " + coretype
print "  smt:          " + smtarg
print "  l1size:       " + l1size
print "  l2type:       " + l2type
print "  l2size:       " + l2size
print "  l3size:       " + l3size
print "  noc:          " + meshtype
print "  memchannels:  " + str(memchan)
print "  memtype:      " + memtype
print ""

if cost > 3500:
    print "ABORT: Cost exceeds limit of 3500. Cost is " + str(cost)
    sys.exit(0)
else:
    print "Cost within limit. Cost is " + str(cost)
print ""


# Set variables for architecture
mesh_clock = 1600
if meshtype == "fast":
    mesh_clock = 2200

memSize = memchan * 2 * 1024 * 1024 * 1024
pages = memSize / 4096
network_bw = str( (mesh_clock * 1000 * 1000 * 36) ) + "B/s"

mesh_stops_x = 5
mesh_stops_y = 5

if corecount > 30:
    mesh_stops_x = 6

if corecount == 40:
    mesh_stops_y = 7
elif corecount > 24:
    mesh_stops_y = 6


corefreq = "4GHz"
maxmemreqpending = 32
if coretype == "slow":
    corefreq = "1.8GHz"
    maxmemreqpending = 16
elif coretype == "medium":
    corefreq = "2.5GHz"
    maxmemreqpending = 16

noc_params = {
    "link_bw" : network_bw,
    "flit_size" : "36B",
    "input_buf_size" : "288KiB"
}

threads = corecount
if smtarg == "yes":
    threads = threads + corecount

# Global problem size
globalmesh = 154 #240
histo = 128
its = 1

genparams = {
    "verbose" : 0,
    "histoslots" : histo,
    "meshx" : globalmesh,
    "meshy" : globalmesh,
    "meshz" : globalmesh,
    "iterations" : its,
}

# Core and SMT configuration
fastcore = {
    "clock" : corefreq,
    "max_reqs_cycle" : 4,
    "max_reorder_lookups" : 32,
    "maxmemreqpending" : maxmemreqpending,
    "pagecount" : pages,
    "pagemap" : "RANDOMIZED"
}

fastcore_smt = {
    "clock" : corefreq,
    "requests_per_cycle" : 4,
}

mediumcore = {
    "clock" : corefreq,
    "max_reqs_cycle" : 2,
    "max_reorder_lookups" : 16,
    "maxmemreqpending" : maxmemreqpending,
    "pagecount" : pages,
    "pagemap" : "RANDOMIZED"
}

mediumcore_smt = {
    "clock" : corefreq,
    "requests_per_cycle" : 2,
}

slowcore = {
    "clock" : corefreq,
    "max_reqs_cycle" : 1,
    "max_reorder_lookups" : 16,
    "maxmemreqpending" : maxmemreqpending,
    "pagecount" : pages,
    "pagemap" : "RANDOMIZED"
}

slowcore_smt = {
    "clock" : corefreq,
    "requests_per_cycle" : 2,
}

# L1 configuration
bigl1 = {
    "cache_frequency" : corefreq,
    "coherence_protocol" : "mesi",
    "replacement_policy" : "lru",
    "cache_size" : "64KiB",
    "associativity" : 16,
    "access_latency_cycles" : 4,
    "tag_access_latency_cycles" : 1,
    "mshr_num_entries" : maxmemreqpending,
    "mshr_latency_cycles" : 1,
    "events_up_per_cycle" : 2,
    "L1" : 1,
    "verbose" : 0,
}

smalll1 = {
    "cache_frequency" : corefreq,
    "coherence_protocol" : "mesi",
    "replacement_policy" : "lru",
    "cache_size" : "16KiB",
    "associativity" : 8,
    "access_latency_cycles" : 1,
    "tag_access_latency_cycles" : 1,
    "mshr_num_entries" : maxmemreqpending,
    "mshr_latency_cycles" : 1,
    "events_up_per_cycle" : 2,
    "L1" : 1,
    "verbose" : 0,
}

# L2 configuration
smalll2 = {
    "cache_frequency" : corefreq,
    "coherence_protocol" : "mesi",
    "replacement_policy" : "nmru",
    "cache_size" : "128KiB",
    "associativity" : 8,
    "access_latency_cycles" : 5,
    "tag_access_latency_cycles" : 2,
    "mshr_latency_cycles" : 2,
    "mshr_num_entries" : maxmemreqpending + 4,
    "debug" : debugL2,
    "debug_level" : debugLev,
}

bigl2 = {
    "cache_frequency" : corefreq,
    "coherence_protocol" : "mesi",
    "replacement_policy" : "nmru",
    "cache_size" : "512KiB",
    "associativity" : 16,
    "access_latency_cycles" : 7,
    "tag_access_latency_cycles" : 3,
    "mshr_latency_cycles" : 3,
    "mshr_num_entries" : maxmemreqpending + 4,
    "debug" : debugL2,
    "debug_level" : debugLev,
}

linkcontrol_params = {
    "link_bw" : network_bw,
    "in_buf_size" : "288B",
    "out_buf_size" : "288B",
}

# L3 configuration
smalll3 = {
    "cache_frequency" : "1.8GHz",
    "coherence_protocol" : "mesi",
    "replacement_policy" : "nmru",
    "cache_size" : "1MiB",
    "associativity" : 16,
    "access_latency_cycles" : 10,
    "tag_access_latency_cycles" : 3,
    "mshr_latency_cycles" : 4,
    "mshr_num_entries" : maxmemreqpending + 8,
    "debug" : debugL3,
    "debug_level" : debugLev,
}

bigl3 = {
    "cache_frequency" : "1.8GHz",
    "coherence_protocol" : "mesi",
    "replacement_policy" : "nmru",
    "cache_size" : "1536KiB",   # 1.5MiB
    "associativity" : 32,
    "access_latency_cycles" : 14,
    "tag_access_latency_cycles" : 4,
    "mshr_latency_cycles" : 4,
    "mshr_num_entries" : maxmemreqpending + 8,
    "debug" : debugL3,
    "debug_level" : debugLev,
}

# Directory configuration
dirctrl_params = {
    "coherence_protocol" : "mesi",
    "clock" : "1.8GHz",
    "entry_cache_size" : 256*1024*1024,
    "mshr_num_entries" : (corecount * maxmemreqpending) / 4,
    "access_latency_cycles" : 4,
}

# Memory configuration
memctrl_params = {
    "clock" : "1200MHz",
    "backing" : "none"
}

basic_memctrl_params = {
    "max_requests_per_cycle" : 2,
}

bw_memctrl_params = {
    "max_requests_per_cycle" : 4,
}

lat_memctrl_params = {
    "max_requests_per_cycle" : 2,
}

basic_mem_params = {
    "id" : 0,
    "addrMapper" : "memHierarchy.simpleAddrMapper",
    "channel.transaction_Q_size" : 32,
    "channel.numRanks" : 2,
    "channel.rank.numBanks" : 16,
    "channel.rank.bank.CL" : 15,
    "channel.rank.bank.CL_WR" : 12,
    "channel.rank.bank.RCD" : 15,
    "channel.rank.bank.TRP" : 15,
    "channel.rank.bank.dataCycles" : 4,
    "channel.rank.bank.pagePolicy" : "memHierarchy.simplePagePolicy",
    "channel.rank.bank.transactionQ" : "memHierarchy.reorderTransactionQ",
    "channel.rank.bank.pagePolicy.close" : 0
}

bw_mem_params = {
    "id" : 0,
    "addrMapper" : "memHierarchy.simpleAddrMapper",
    "channel.transaction_Q_size" : 48,
    "channel.numRanks" : 4,
    "channel.rank.numBanks" : 32,
    "channel.rank.bank.CL" : 15,
    "channel.rank.bank.CL_WR" : 12,
    "channel.rank.bank.RCD" : 15,
    "channel.rank.bank.TRP" : 15,
    "channel.rank.bank.dataCycles" : 4,
    "channel.rank.bank.pagePolicy" : "memHierarchy.simplePagePolicy",
    "channel.rank.bank.transactionQ" : "memHierarchy.reorderTransactionQ",
    "channel.rank.bank.pagePolicy.close" : 0
}


lat_mem_params = {
    "id" : 0,
    "addrMapper" : "memHierarchy.simpleAddrMapper",
    "channel.transaction_Q_size" : 32,
    "channel.numRanks" : 2,
    "channel.rank.numBanks" : 16,
    "channel.rank.bank.CL" : 11,
    "channel.rank.bank.CL_WR" : 8,
    "channel.rank.bank.RCD" : 11,
    "channel.rank.bank.TRP" : 11,
    "channel.rank.bank.dataCycles" : 2,
    "channel.rank.bank.pagePolicy" : "memHierarchy.simplePagePolicy",
    "channel.rank.bank.transactionQ" : "memHierarchy.reorderTransactionQ",
    "channel.rank.bank.pagePolicy.close" : 0
}

# This class partitions the workload over the cores and also returns the location of the memories on the mesh
class MeshPartitioner:
    def __init__(self, corecount, memchan):
        if corecount == 22:
            self.xb, self.xe, self.yb, self.ye, self.zb, self.ze, self.mc = self.partition22(memchan)
        elif corecount == 24:
            self.xb, self.xe, self.yb, self.ye, self.zb, self.ze, self.mc = self.partition24(memchan)
        elif corecount == 30:
            self.xb, self.xe, self.yb, self.ye, self.zb, self.ze, self.mc = self.partition30(memchan)
        elif corecount == 32:
            self.xb, self.xe, self.yb, self.ye, self.zb, self.ze, self.mc = self.partition32(memchan)
        elif corecount == 36:
            self.xb, self.xe, self.yb, self.ye, self.zb, self.ze, self.mc = self.partition36(memchan)
        else:
            self.xb, self.xe, self.yb, self.ye, self.zb, self.ze, self.mc = self.partition40(memchan)


    def getPartitionForCore(self, core_id):
        return self.xb[core_id], self.xe[core_id], self.yb[core_id], self.ye[core_id], self.zb[core_id], self.ze[core_id]

    def getLocForMC(self, mc_id):
        return self.mc[mc_id]

    def partition22(self, mcs):
        # Subtract boundary
        meshpt = globalmesh - 2
        
        # Compute x partitioning
        x0 = int(2 * meshpt / 11)
        x1 = x0 + ((meshpt - x0) // 2)
        x2 = meshpt
        xe = [ x0, x0, x0, x0, x1, x1, x1, x1, x1, x1, x1, x1, x1, x2, x2, x2, x2, x2, x2, x2, x2, x2]
        xb = [ 1, 1, 1, 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1]

        # Compute y & z partitioning
        y0 = meshpt // 2
        y1 = meshpt
        y2 = meshpt // 3
        y3 = ((meshpt - y2) // 2) + y2
        ye = [y0, y0, y1, y1, y2, y2, y2, y3, y3, y3, y1, y1, y1, y2, y2, y2, y3, y3, y3, y1, y1, y1]
        yb = [1, 1, y0 + 1, y0 + 1, 1, 1, 1, y2 + 1, y2 + 1, y2 + 1, y3 + 1, y3 + 1, y3 + 1, 1, 1, 1, y2 + 1, y2 + 1, y2 + 1, y3 + 1, y3 + 1, y3 + 1]
        ze = [y0, y1, y0, y1, y2, y3, y1, y2, y3, y1, y2, y3, y1, y2, y3, y1, y2, y3, y1, y2, y3, y1]
        zb = [1, y0 + 1, 1, y0 + 1, 1, y2 + 1, y3 + 1, 1, y2 + 1, y3 + 1, 1, y2 + 1, y3 + 1, 1, y2 + 1, y3 + 1, 1, y2 + 1, y3 + 1, 1, y2 + 1, y3 + 1]

        if mcs == 6:
            mc = [1,3,21,23,10,14]
        else:
            mc = [1,3,21,23,5,9,15,19]
        return xb, xe, yb, ye, zb, ze, mc
    
    def partition24(self, mcs):
        # Subtract boundary
        meshpt = globalmesh - 2

        # Compute x partitioning
        x0 = int(meshpt / 4)
        x1 = ((meshpt - x0) // 2) + x0
        x2 = meshpt
        xe = [x0, x0, x0, x0, x0, x0, x1, x1, x1, x1, x1, x1, x1, x1, x1, x2, x2, x2, x2, x2, x2, x2, x2, x2]
        xb = [1,  1,  1,  1,  1,  1,  x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1]

        # Compute y partitioning
        y0 = meshpt // 3
        y1 = ((meshpt - y0) // 2) + y0
        y2 = meshpt
        ye = [y0, y0, y1, y1, y2, y2, y0, y0, y0, y1, y1, y1, y2, y2, y2, y0, y0, y0, y1, y1, y1, y2, y2, y2]
        yb = [1, 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, 1, 1, 1, y0 + 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, y1 + 1, 1, 1, 1, y0 + 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, y1 + 1]
        
        # Compute z partitioning
        z0 = meshpt // 2
        z1 = meshpt // 3
        z2 = ((meshpt - z1) // 2) + z1
        z3 = meshpt
        ze = [z0, z3, z0, z3, z0, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3]
        zb = [1,  z0 + 1, 1,  z0 + 1, 1, z0 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1]
        
        if mcs == 6:
            mc = [1,3,21,23,10,14]
        else:
            mc = [1,3,21,23,5,9,15,19]

        return xb, xe, yb, ye, zb, ze, mc

    def partition30(self, mcs):
        # Subtract boundary
        meshpt = globalmesh - 2
        
        # Compute x partitioning
        x1 = int(2 * meshpt / 5)
        x0 = x1 // 2
        x2 = ((meshpt - x1) // 2) + x1
        x3 = meshpt
        xe = [x0, x0, x0, x0, x0, x0, x1, x1, x1, x1, x1, x1, x2, x2, x2, x2, x2, x2, x2, x2, x2, x3, x3, x3, x3, x3, x3, x3, x3, x3]
        xb = [1, 1, 1, 1, 1, 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1]

        # Compute y partitioning
        y0 = meshpt // 3
        y1 = ((meshpt - y0) // 2) + y0
        y2 = meshpt
        ye = [y0, y0, y1, y1, y2, y2, y0, y0, y1, y1, y2, y2, y0, y0, y0, y1, y1, y1, y2, y2, y2, y0, y0, y0, y1, y1, y1, y2, y2, y2]
        yb = [1, 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, 1, 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, 1, 1, 1, y0 + 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, y1 + 1, 1, 1, 1, y0 + 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, y1 + 1]

        # Compute z partitioning
        z0 = meshpt // 2
        z1 = meshpt // 3
        z2 = ((meshpt - z1) // 2) + z1
        z3 = meshpt
        ze = [z0, z3, z0, z3, z0, z3, z0, z3, z0, z3, z0, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3]
        zb = [1, z0 + 1, 1, z0 + 1, 1, z0 + 1, 1, z0 + 1, 1, z0 + 1, 1, z0 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1]
        
        if mcs == 6:
            mc = [1,3,26,28,15,14]
        else:
            mc = [1,3,26,28,10,14,15,19]

        return xb, xe, yb, ye, zb, ze, mc
    
    def partition32(self, mcs):
        # Subtract boundary
        meshpt = globalmesh - 2
        
        # Compute x partitioning
        x1 = int( meshpt / 4 )
        x0 = x1 // 2
        x2 = ((meshpt - x1) // 2) + x1
        x3 = meshpt
        xe = [x0, x0, x0, x0, x1, x1, x1, x1, x2, x2, x2, x2, x2, x2, x2, x2, x2, x2, x2, x2, x3, x3, x3, x3, x3, x3, x3, x3, x3, x3, x3, x3]
        xb = [1, 1, 1, 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, 
                x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1]
        
        # Compute y partitioning
        y0 = meshpt // 2
        y1 = meshpt // 4
        y2 = ((meshpt - y1) // 3) + y1
        y3 = ((meshpt - y2) // 2) + y2
        y4 = meshpt
        ye = [y0, y0, y4, y4, y0, y0, y4, y4, y1, y1, y1, y2, y2, y2, y3, y3, y3, y4, y4, y4, y1, y1, y1, y2, y2, y2, y3, y3, y3, y4, y4, y4]
        yb = [1, 1, y0 + 1, y0 + 1, 1, 1, y0 + 1, y0 + 1, 1, 1, 1, y1 + 1, y1 + 1, y1 + 1, y2 + 1, y2 + 1, y2 + 1, y3 + 1, y3 + 1, y3 + 1, 1, 1, 1, y1 + 1, y1 + 1, y1 + 1, y2 + 1, y2 + 1, y2 + 1, y3 + 1, y3 + 1, y3 + 1]
                
        # Compute z partitioning
        z0 = meshpt // 2
        z1 = meshpt // 3
        z2 = ((meshpt - z1) // 2) + z1
        z3 = meshpt
        ze = [z0, z3, z0, z3, z0, z3, z0, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3]
        zb = [1, z0 + 1, 1, z0 + 1, 1, z0 + 1, 1, z0 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1]
                
        if mcs == 6:
            mc = [2,3,32,33,18,17]
        else:
            mc = [2,3,32,33,12,17,18,23]

        return xb, xe, yb, ye, zb, ze, mc

    def partition36(self, mcs):
        # Subtract boundary
        meshpt = globalmesh - 2
        
        # Compute x partitioning
        x0 = meshpt // 4
        x1 = ((meshpt - x0) // 3) + x0
        x2 = ((meshpt - x1) // 2) + x1
        x3 = meshpt
        
        xe = [x0, x0, x0, x0, x0, x0, x0, x0, x0, x1, x1, x1, x1, x1, x1, x1, x1, x1, x2, x2, x2, x2, x2, x2, x2, x2, x2, x3, x3, x3, x3, x3, x3, x3, x3, x3]
        xb = [1, 1, 1, 1, 1, 1, 1, 1, 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, 
                x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1]

        # Compute y & z partitioning
        y0 = meshpt // 3
        y1 = ((meshpt - y0) // 2) + y0
        y2 = meshpt
        ye = [y0, y0, y0, y1, y1, y1, y2, y2, y2, y0, y0, y0, y1, y1, y1, y2, y2, y2, y0, y0, y0, y1, y1, y1, y2, y2, y2, y0, y0, y0, y1, y1, y1, y2, y2, y2]
        ze = [y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2, y0, y1, y2]
        yb = [1, 1, 1, y0 + 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, y1 + 1, 1, 1, 1, y0 + 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, y1 + 1, 1, 1, 1, y0 + 1, y0 + 1, 
                y0 + 1, y1 + 1, y1 + 1, y1 + 1, 1, 1, 1, y0 + 1, y0 + 1, y0 + 1, y1 + 1, y1 + 1, y1 + 1]
        zb = [1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 
                1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1, 1, y0 + 1, y1 + 1]
        
        if mcs == 6:
            mc = [2,3,32,33,18,17]
        else:
            mc = [2,3,32,33,12,17,18,23]

        return xb, xe, yb, ye, zb, ze, mc

    def partition40(self, mcs):
        # Subtract boundary
        meshpt = globalmesh - 2
        
        # Compute x partitioning
        x0 = int (meshpt // 10)
        x1 = ((meshpt - x0) // 3) + x0
        x2 = ((meshpt - x1) // 2) + x1
        x3 = meshpt
        xe = [x0, x0, x0, x0, x1, x1, x1, x1, x1, x1, x1, x1, x1, x1, x1, x1, x2, x2, x2, x2, x2, x2, x2, x2, x2, x2, x2, x2, x3, x3, x3, x3, x3, x3, x3, x3, x3, x3, x3, x3]
        xb = [1, 1, 1, 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x0 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, x1 + 1, 
                x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1, x2 + 1]

        # Compute y partitioning
        y0 = meshpt // 2
        y1 = meshpt // 4
        y2 = ((meshpt - y1) // 3) + y1
        y3 = ((meshpt - y2) // 2) + y2
        y4 = meshpt
        ye = [y0, y0, y4, y4, y1, y1, y1, y2, y2, y2, y3, y3, y3, y4, y4, y4, y1, y1, y1, y2, y2, y2, y3, y3, y3, y4, y4, y4, y1, y1, y1, y2, y2, y2, y3, y3, y3, y4, y4, y4]
        yb = [1, 1, y0 + 1, y0 + 1, 1, 1, 1, y1 + 1, y1 + 1, y1 + 1, y2 + 1, y2 + 1, y2 + 1, y3 + 1, y3 + 1, y3 + 1, 1, 1, 1, y1 + 1, y1 + 1, y1 + 1, y2 + 1, y2 + 1, y2 + 1, y3 + 1, y3 + 1, y3 + 1, 
                1, 1, 1, y1 + 1, y1 + 1, y1 + 1, y2 + 1, y2 + 1, y2 + 1, y3 + 1, y3 + 1, y3 + 1]

        # Compute z partitioning
        z0 = meshpt // 2
        z1 = meshpt // 3
        z2 = ((meshpt - z1) // 2) + z1
        z3 = meshpt
        ze = [z0, z3, z0, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3, z1, z2, z3]
        zb = [1, z0 + 1, 1, z0 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1,
                1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1, 1, z1 + 1, z2 + 1]

        if mcs == 6:
            mc = [2,3,38,39,18,23]
        else:
            mc = [2,3,38,39,12,17,24,29]

        return xb, xe, yb, ye, zb, ze, mc


mp = MeshPartitioner(corecount, memchan)

# Create NoC 
kRtr=[] # Router links for nodes
node = 0
for x in range(0, mesh_stops_x):
    for y in range(0, mesh_stops_y):
        kRtr.append(sst.Component("rtr_" + str(node), "kingsley.noc_mesh"))
        kRtr[-1].addParams(noc_params)
        if l2type == "private":
            kRtr[-1].addParams({"local_ports" : 2}) # L2 & L3
        else:
            kRtr[-1].addParams({"local_ports" : 3}) # L1, L2, & L3
        node = node + 1

# Connect routers in mesh
node = 0
for y in range(0, mesh_stops_y):
    for x in range(0, mesh_stops_x):
        if y != (mesh_stops_y - 1): # Not the bottom row
            kRtrNS = sst.Link("link_rtr_ns_" + str(node))
            kRtrNS.connect( (kRtr[node], "south", "300ps"), (kRtr[node + mesh_stops_x], "north", "300ps") )
        
        if x != (mesh_stops_x - 1): # Not the right-most column
            kRtrEW = sst.Link("link_rtr_ew_" + str(node))
            kRtrEW.connect( (kRtr[node], "east", "300ps"), (kRtr[node+1], "west", "300ps") )

        node = node + 1


# Create memories & directories and place on mesh
for x in range(0, memchan):
    dirctrl = sst.Component("dirctrl" + str(x), "memHierarchy.DirectoryController")
    dirctrl.addParams(dirctrl_params)
    dirNoc = dirctrl.setSubComponent("cpulink", "memHierarchy.MemNIC")
    dirNoc.addParams({ "group" : 3 })

    dirNocCtrl = dirNoc.setSubComponent("linkcontrol", "kingsley.linkcontrol")
    dirNocCtrl.addParams(linkcontrol_params)
    dirMem = dirctrl.setSubComponent("memlink", "memHierarchy.MemLink")

    memctrl = sst.Component("memctrl" + str(x), "memHierarchy.MemController")
    memctrl.addParams(memctrl_params)
    mem = memctrl.setSubComponent("backend", "memHierarchy.timingDRAM")
    mem.addParams({ "mem_size" : "2GiB" })
    if memtype == "basic":
        mem.addParams(basic_mem_params)
        memctrl.addParams(basic_memctrl_params)
    elif memtype == "bw":
        mem.addParams(bw_mem_params)
        memctrl.addParams(bw_memctrl_params)
    else:
        mem.addParams(lat_mem_params)
        memctrl.addParams(lat_memctrl_params)

    dirToMem = sst.Link("dir_to_mem_" + str(x))
    dirToMem.connect( (dirMem, "port", "500ps"), (memctrl, "direct_link", "500ps") )
    
    dirctrl.addParams({
        "interleave_size" : "64B",    # Interleave at line granularity between memories
        "interleave_step" : str(memchan * 64) + "B",
        "addr_range_start" : x*64,
        "addr_range_end" :  (memchan * 2 * 1024 * 1024 * 1024) - ((memchan - x) * 64) + 63,
    })
    memctrl.addParams({
        "interleave_size" : "64B",    # Interleave at line granularity between memories
        "interleave_step" : str(memchan * 64) + "B",
        "addr_range_start" : x*64,
        "addr_range_end" :  (memchan * 2 * 1024 * 1024 * 1024) - ((memchan - x) * 64) + 63,
    })

    rtrlink = sst.Link("link_rtr_mem_" + str(x))
    loc = mp.getLocForMC(x)
    if x < 2:
        rtrlink.connect( (kRtr[loc], "north", "300ps"), (dirNocCtrl, "rtr_port", "300ps") ) 
    elif x < 4:
        rtrlink.connect( (kRtr[loc], "south", "300ps"), (dirNocCtrl, "rtr_port", "300ps") )
    elif x == 4 or x == 6:
        rtrlink.connect( (kRtr[loc], "west", "300ps"), (dirNocCtrl, "rtr_port", "300ps") )
    else:
        rtrlink.connect( (kRtr[loc], "east", "300ps"), (dirNocCtrl, "rtr_port", "300ps") )

# Create cores & caches and place on mesh
for x in range(0, corecount):
    
    # L1 caches
    l1 = sst.Component("l1cache" + str(x), "memHierarchy.Cache")
    if l1size == "big":
        l1.addParams(bigl1)
    else: # small
        l1.addParams(smalll1)
    l1uplink = l1.setSubComponent("cpulink", "memHierarchy.MemLink")
    
    # Partition mesh
    beginx, endx, beginy, endy, beginz, endz = mp.getPartitionForCore(x)

    if smtarg == "no":
        core = sst.Component("core" + str(x), "miranda.BaseCPU")
        if coretype == "slow":
            core.addParams(slowcore)
        elif coretype == "medium":
            core.addParams(mediumcore)
        else: # fast
            core.addParams(fastcore)
    
        gen = core.setSubComponent("generator", "sc19.WorkloadGenerator")
        gen.addParams(genparams)
        gen.addParams(
                { "seed" : x + 8471,
                  "beginx" : beginx,
                  "beginy" : beginy,
                  "beginz" : beginz,
                  "endx" : endx,
                  "endy" : endy,
                  "endz" : endz 
                })
        
        coreToL1 = sst.Link("link_core_to_l1_" + str(x))
        coreToL1.connect( (core, "cache_link", "100ps"), (l1uplink, "port", "100ps") )
    else: # using SMT
        core0 = sst.Component("core" + str(x) + ".0", "miranda.BaseCPU")
        core1 = sst.Component("core" + str(x) + ".1", "miranda.BaseCPU")
        smt = sst.Component("smt" + str(x), "memHierarchy.multithreadL1")
        
        splitz = (endz - beginz) / 2

        gen0 = core0.setSubComponent("generator", "sc19.WorkloadGenerator")
        gen0.addParams(genparams)
        gen0.addParams(
                { "seed" : x + 8471,
                  "beginx" : beginx,
                  "beginy" : beginy,
                  "beginz" : beginz,
                  "endx" : endx,
                  "endy" : endy,
                  "endz" : beginz + splitz 
                })
        gen1 = core1.setSubComponent("generator", "sc19.WorkloadGenerator")
        gen1.addParams(genparams)
        gen1.addParams(
                { "seed" : x + 4575,
                  "beginx" : beginx,
                  "beginy" : beginy,
                  "beginz" : beginz + splitz + 1,
                  "endx" : endx,
                  "endy" : endy,
                  "endz" : endz 
                })

        if coretype == "slow":
            core0.addParams(slowcore)
            core1.addParams(slowcore)
            smt.addParams(slowcore_smt)
        elif coretype == "medium":
            core0.addParams(mediumcore)
            core1.addParams(mediumcore)
            smt.addParams(mediumcore_smt)
        else: # fast
            core0.addParams(fastcore)
            core1.addParams(fastcore)
            smt.addParams(fastcore_smt)
        
        core0ToSMT = sst.Link("smt_core0_" + str(x))
        core0ToSMT.connect((core0, "cache_link", "100ps"), (smt, "thread0", "100ps"))
        core1ToSMT = sst.Link("smt_core1_" + str(x))
        core1ToSMT.connect((core1, "cache_link", "100ps"), (smt, "thread1", "100ps"))
        coreToL1 = sst.Link("link_core_to_l1_" + str(x))
        coreToL1.connect( (smt, "cache", "100ps"), (l1uplink, "port", "100ps") )
        
    # L2 caches
    l2 = sst.Component("l2cache" + str(x), "memHierarchy.Cache")
    if l2size == "big":
        l2.addParams(bigl2)
    else:
        l2.addParams(smalll2)
    if l2type == "private":
        l1downlink = l1.setSubComponent("memlink", "memHierarchy.MemLink")
        l2uplink = l2.setSubComponent("cpulink", "memHierarchy.MemLink")
        L1ToL2 = sst.Link("link_l1_to_l2_" + str(x))
        L1ToL2.connect( (l1downlink, "port", "100ps"), (l2uplink, "port", "100ps") )
        
        l2nic = l2.setSubComponent("memlink", "memHierarchy.MemNIC")
        l2nic.addParams({ "group" : 1 })
        l2nicCtrl = l2nic.setSubComponent("linkcontrol", "kingsley.linkcontrol")
        l2nicCtrl.addParams(linkcontrol_params)
        L2toNoc = sst.Link("link_l2_to_NoC_" + str(x))
        L2toNoc.connect( (l2nicCtrl, "rtr_port", "300ps"), (kRtr[x], "local1", "300ps") )
    else: # shared
        l2.addParams({
            "num_cache_slices" : corecount,
            "slice_id" : x
        })
        l1nic = l1.setSubComponent("memlink", "memHierarchy.MemNIC")
        l1nic.addParams({ "group" : 0 })
        l1nicCtrl = l1nic.setSubComponent("linkcontrol", "kingsley.linkcontrol")
        l1nicCtrl.addParams(linkcontrol_params)
        L1toNoc = sst.Link("link_l1_to_NoC_" + str(x))
        L1toNoc.connect( (l1nicCtrl, "rtr_port", "300ps"), (kRtr[x], "local2", "300ps") )
        
        l2nic = l2.setSubComponent("cpulink", "memHierarchy.MemNIC")
        l2nic.addParams({ "group" : 1 })
        l2nicCtrl = l2nic.setSubComponent("linkcontrol", "kingsley.linkcontrol")
        l2nicCtrl.addParams(linkcontrol_params)
        L2toNoc = sst.Link("link_l2_to_Noc_" + str(x))
        L2toNoc.connect( (l2nicCtrl, "rtr_port", "300ps"), (kRtr[x], "local1", "300ps") )

    # L3 banks
    l3 = sst.Component("l3cache" + str(x), "memHierarchy.Cache")
    if l3size == "big":
        l3.addParams(bigl3)
    else: # small
        l3.addParams(smalll3)
    l3.addParams({
        "num_cache_slices" : corecount,
        "slice_id" : x
    })
    l3nic = l3.setSubComponent("cpulink", "memHierarchy.MemNIC")
    l3nic.addParams({ "group" : 2 })
    l3nicCtrl = l3nic.setSubComponent("linkcontrol", "kingsley.linkcontrol")
    l3nicCtrl.addParams(linkcontrol_params)
    L3toNoc = sst.Link("link_l3_to_NoC_" + str(x))
    L3toNoc.connect( (l3nicCtrl, "rtr_port", "300ps"), (kRtr[x], "local0", "300ps") )

