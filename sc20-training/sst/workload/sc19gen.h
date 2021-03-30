// Copyright 2009-2019 NTESS. Under the terms
// of Contract DE-NA0003525 with NTESS, the U.S.
// Government retains certain rights in this software.
//
// Copyright (c) 2009-2019, NTESS
// All rights reserved.
//
// Portions are copyright of other developers:
// See the file CONTRIBUTORS.TXT in the top level directory
// the distribution for more information.
//
// This file is part of the SST software package. For license
// information, see the LICENSE file in the top level directory of the
// distribution.

#ifndef _H_SST_MIRANDA_SC19_GEN
#define _H_SST_MIRANDA_SC19_GEN

#include <sst/core/output.h>
#include <sst/core/rng/sstrng.h>
#include <sst/elements/miranda/mirandaGenerator.h>

#include <queue>

using namespace SST::RNG;

namespace SST {
namespace Miranda {

class WorkloadGenerator : public RequestGenerator {

public:
  WorkloadGenerator(Component *owner, Params &params);
  WorkloadGenerator(ComponentId_t id, Params &params);
  void build(Params &params);
  ~WorkloadGenerator();
  void generate(MirandaRequestQueue<GeneratorRequest *> *q);
  uint64_t getMemoryLocation(const uint32_t x, const uint32_t y,
                             const uint32_t z);
  bool isFinished();
  void completed();

  SST_ELI_REGISTER_SUBCOMPONENT_DERIVED(
      WorkloadGenerator, "sc19", "WorkloadGenerator",
      SST_ELI_ELEMENT_VERSION(1, 0, 0),
      "Creates a workload for SC19 simulations.",
      SST::Miranda::RequestGenerator)

  SST_ELI_DOCUMENT_PARAMS(
      {"verbose", "Sets the verbosity output of the generator", "0"},
      {"histoslots", "Number of histogram slots to simulate result bins.",
       "32"},
      {"meshx", "Mesh points in X", "32"}, {"meshy", "Mesh points in Y", "32"},
      {"meshz", "Mesh points in Z", "32"},
      {"beginx", "Local starting point in X", "1"},
      {"beginy", "Local starting point in Y", "1"},
      {"beginz", "Local starting point in Z", "1"},
      {"meshx", "Local ending point in X", "32"},
      {"meshy", "Local ending point in Y", "32"},
      {"meshz", "Local ending point in Z", "32"},
      {"iterations", "Number of iterations to perform", "1"},
      {"seed", "Random number seed", "10101"}, )
private:
  uint32_t meshX;
  uint32_t meshY;
  uint32_t meshZ;

  uint32_t beginX;
  uint32_t beginY;
  uint32_t beginZ;

  uint32_t endX;
  uint32_t endY;
  uint32_t endZ;

  uint32_t currentX;
  uint32_t currentY;
  uint32_t currentZ;

  uint32_t maxItr;
  uint32_t currentItr;
  uint32_t histoslots;
  uint32_t histoindex;

  bool phase;

  SSTRandom *rng;
  Output *out;
};

} // namespace Miranda
} // namespace SST

#endif
