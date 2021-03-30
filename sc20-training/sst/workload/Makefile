CXX=$(shell sst-config --CXX)
CXXFLAGS=$(shell sst-config --ELEMENT_CXXFLAGS)
LDFLAGS=$(shell sst-config --ELEMENT_LDFLAGS)

### EDIT THESE TWO LINES to point to the source directory for sst-elements and the install directory for sst-core
SSTELEMSOURCE=/home/sst-elements/
SSTCOREINSTALL=/home/sst-build/sst-core/

CPPFLAGS=-I./ -I$(SSTELEMSOURCE)/src -I$(SSTCOREINSTALL)/include/sst/core
OPTIMIZE_FLAGS=-O3

WORKLOAD_SOURCES := $(wildcard *.cc)
WORKLOAD_HEADERS := $(wildcard *.h)

WORKLOAD_OBJS := $(patsubst %.cc,%.o,$(wildcard *.cc))

all: libsc19.so install

libsc19.so: $(WORKLOAD_OBJS)
	$(CXX) $(OPTIMIZE_FLAGS) $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -o $@ *.o

%.o:%.cc $(WORKLOAD_HEADERS)
	$(CXX) $(OPTIMIZE_FLAGS) $(CXXFLAGS) $(CPPFLAGS) -c $<

install:
	sst-register sc19 sc19_LIBDIR=$(CURDIR)

clean:
	rm -f *.o

