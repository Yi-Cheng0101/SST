
#include <sst/core/params.h>
#include <sst/core/rng/xorshift.h>
#include <sst_config.h>

#include "sc19gen.h"

using namespace SST::RNG;
using namespace SST::Miranda;

WorkloadGenerator::WorkloadGenerator(Component *owner, Params &params)
    : RequestGenerator(owner, params) {
  build(params);
}

WorkloadGenerator::WorkloadGenerator(ComponentId_t id, Params &params)
    : RequestGenerator(id, params) {
  build(params);
}

void WorkloadGenerator::build(Params &params) {
  const uint32_t verbose = params.find<uint32_t>("verbose", 0);

  out = new Output("SC19[@p:@l]: ", verbose, 0, Output::STDOUT);

  maxItr = params.find<uint32_t>("iterations", 1);
  meshX = params.find<uint32_t>("meshx", 32);
  meshY = params.find<uint32_t>("meshy", 32);
  meshZ = params.find<uint32_t>("meshz", 32);

  beginX = params.find<uint32_t>("beginx", 1);
  beginY = params.find<uint32_t>("beginy", 1);
  beginZ = params.find<uint32_t>("beginz", 1);
  endX = params.find<uint32_t>("endx", 30);
  endY = params.find<uint32_t>("endy", 30);
  endZ = params.find<uint32_t>("endz", 30);

  histoslots = params.find<uint32_t>("histoslots", 32);
  histoindex = 0;

  currentItr = 0;
  currentX = beginX;
  currentY = beginY;
  currentZ = beginZ;

  uint32_t seed = params.find<uint32_t>("seed", 101011);
  rng = new XORShiftRNG(seed);

  phase = false;

  out->verbose(CALL_INFO, 4, 0, "Parameters for SC19 Workload:\n");
  out->verbose(CALL_INFO, 4, 0, "-> Mesh-X:              %10" PRIu32 "\n",
               meshX);
  out->verbose(CALL_INFO, 4, 0, "-> Mesh-Y:              %10" PRIu32 "\n",
               meshY);
  out->verbose(CALL_INFO, 4, 0, "-> Mesh-Z:              %10" PRIu32 "\n",
               meshZ);
  out->verbose(CALL_INFO, 4, 0,
               "-> Local X:             %10" PRIu32 " - %10" PRIu32 "\n",
               beginX, endX);
  out->verbose(CALL_INFO, 4, 0,
               "-> Local Y:             %10" PRIu32 " - %10" PRIu32 "\n",
               beginY, endY);
  out->verbose(CALL_INFO, 4, 0,
               "-> Local Z:             %10" PRIu32 " - %10" PRIu32 "\n",
               beginZ, endZ);
  out->verbose(CALL_INFO, 4, 0, "-> Iterations:          %10" PRIu32 "\n",
               maxItr);
  out->verbose(CALL_INFO, 4, 0, "-> Histo-Slots:         %10" PRIu32 "\n",
               histoslots);
}

WorkloadGenerator::~WorkloadGenerator() {
  delete rng;
  delete out;
}

uint64_t WorkloadGenerator::getMemoryLocation(const uint32_t x,
                                              const uint32_t y,
                                              const uint32_t z) {
  return static_cast<uint64_t>((histoslots * 8) + (8 * z * meshX * meshY) +
                               (8 * y * meshX) + (8 * x));
}

void WorkloadGenerator::generate(MirandaRequestQueue<GeneratorRequest *> *q) {
  out->verbose(CALL_INFO, 16, 0,
               "%s, Itr=%5" PRIu32 ", Phase=%d, X=%" PRIu32 ", Y=%8" PRIu32
               ", Z=%8" PRIu32 "\n",
               getName().c_str(), currentItr, phase, currentX, currentY,
               currentZ);

  if (currentZ == endZ && currentY == endY && currentX == endX) {

    out->verbose(CALL_INFO, 4, 0, "Iteration %" PRIu32 " is complete.\n",
                 currentItr);

    currentItr++;
    currentX = beginX;
    currentY = beginY;
    currentZ = beginZ;

    histoindex = 0;
    if ((currentItr % 3) == 2) {
      phase = true;
    } else {
      phase = false;
    }

  } else if (phase) {
    if (currentX > endX) {
      if (currentY < endY) {
        currentX = beginX;
        currentY++;
      } else {
        currentX = beginX;
        currentY = beginY;
        currentZ++;
      }
    }

    MemoryOpRequest *read_histo =
        new MemoryOpRequest((histoindex * 8), 8, READ);
    uint64_t do_write = (rng->generateNextUInt64() % 2);
    if (do_write == 1) {
      MemoryOpRequest *update_mesh = new MemoryOpRequest(
          getMemoryLocation(currentX, currentY, currentZ), 8, WRITE);
      update_mesh->addDependency(read_histo->getRequestID());
      q->push_back(read_histo);
      q->push_back(update_mesh);
      out->verbose(
          CALL_INFO, 8, 0,
          "%s, Itr=%5" PRIu32 ", Phase=%d, X=%" PRIu32 ", Y=%8" PRIu32
          ", Z=%8" PRIu32 ", RAddr=0x%" PRIx64 ", WAddr=0x%" PRIx64 "\n",
          getName().c_str(), currentItr, phase, currentX, currentY, currentZ,
          read_histo->getAddress(), update_mesh->getAddress());
    } else {
      q->push_back(read_histo);
      out->verbose(CALL_INFO, 8, 0,
                   "%s, Itr=%5" PRIu32 ", Phase=%d, X=%" PRIu32 ", Y=%8" PRIu32
                   ", Z=%8" PRIu32 ", RAddr=0x%" PRIx64 "\n",
                   getName().c_str(), currentItr, phase, currentX, currentY,
                   currentZ, read_histo->getAddress());
    }

    histoindex++;
    if (histoindex == histoslots)
      histoindex = 0;
    currentX++;
  } else {
    if (currentX > endX) {
      if (currentY < endY) {
        currentX = beginX;
        currentY++;
      } else {
        currentX = beginX;
        currentY = beginY;
        currentZ++;
      }
    }

    MemoryOpRequest *read_xone_req = new MemoryOpRequest(
        getMemoryLocation(currentX + 1, currentY, currentZ), 8, READ);
    MemoryOpRequest *read_xnegone_req = new MemoryOpRequest(
        getMemoryLocation(currentX - 1, currentY, currentZ), 8, READ);
    MemoryOpRequest *read_center_req = new MemoryOpRequest(
        getMemoryLocation(currentX, currentY, currentZ), 8, READ);
    MemoryOpRequest *read_yone_req = new MemoryOpRequest(
        getMemoryLocation(currentX, currentY + 1, currentZ), 8, READ);
    MemoryOpRequest *read_ynegone_req = new MemoryOpRequest(
        getMemoryLocation(currentX, currentY - 1, currentZ), 8, READ);
    MemoryOpRequest *read_zone_req = new MemoryOpRequest(
        getMemoryLocation(currentX, currentY, currentZ + 1), 8, READ);
    MemoryOpRequest *read_znegone_req = new MemoryOpRequest(
        getMemoryLocation(currentX, currentY, currentZ - 1), 8, READ);

    const uint64_t write_loc = (rng->generateNextUInt64() % histoslots) * 8;
    out->verbose(CALL_INFO, 4, 0, "Histo-slot: %" PRIu64 "\n", write_loc);
    MemoryOpRequest *write_histo = new MemoryOpRequest(write_loc, 8, WRITE);

    out->verbose(CALL_INFO, 8, 0,
                 "%s, Itr=%5" PRIu32 ", Phase=%d, X=%" PRIu32 ", Y=%8" PRIu32
                 ", Z=%8" PRIu32 ", R0=0x%" PRIx64 ", R1=%" PRIx64
                 ", R2=0x%" PRIx64 ", R3=%" PRIx64 ", R4=0x%" PRIx64
                 ", R5=0x%" PRIx64 ", R6=0x%" PRIx64 ", W=0x%" PRIx64 "\n",
                 getName().c_str(), currentItr, phase, currentX, currentY,
                 currentZ, read_xone_req->getAddress(),
                 read_xnegone_req->getAddress(), read_center_req->getAddress(),
                 read_yone_req->getAddress(), read_ynegone_req->getAddress(),
                 read_zone_req->getAddress(), read_znegone_req->getAddress(),
                 write_loc);

    write_histo->addDependency(read_center_req->getRequestID());
    write_histo->addDependency(read_zone_req->getRequestID());
    write_histo->addDependency(read_znegone_req->getRequestID());
    write_histo->addDependency(read_yone_req->getRequestID());
    write_histo->addDependency(read_ynegone_req->getRequestID());
    write_histo->addDependency(read_xone_req->getRequestID());
    write_histo->addDependency(read_xnegone_req->getRequestID());

    q->push_back(read_center_req);
    q->push_back(read_xone_req);
    q->push_back(read_xnegone_req);
    q->push_back(read_yone_req);
    q->push_back(read_ynegone_req);
    q->push_back(read_zone_req);
    q->push_back(read_znegone_req);

    q->push_back(write_histo);

    currentX++;
  }
}

bool WorkloadGenerator::isFinished() { return currentItr == maxItr; }

void WorkloadGenerator::completed() {}
