#include "PulseScheduler.hpp"
#include "InstructionIterator.hpp"
#include "Pulse.hpp"

#include "xacc.hpp"

namespace {
  void processComposite(std::shared_ptr<xacc::CompositeInstruction> composite, size_t compositeStartTime, std::map<std::string, std::size_t>& io_channel2times) {
    for (auto& inst: composite->getInstructions()) {
      if (inst->isEnabled() && !inst->isComposite()) {
        auto pulse = std::dynamic_pointer_cast<xacc::quantum::Pulse>(inst);
        if (!pulse) {
            xacc::error("Invalid instruction in pulse program.");
        }
        if (io_channel2times.find(pulse->channel()) == io_channel2times.end()) {
          io_channel2times.insert({pulse->channel(), compositeStartTime});
        }
        auto& currentTimeOnChannel = io_channel2times[pulse->channel()];
        auto pulseExpectedStart = pulse->start() + compositeStartTime;
        if (pulseExpectedStart >= currentTimeOnChannel) {
          pulse->setStart(pulseExpectedStart);
        } else {
          pulse->setStart(currentTimeOnChannel);
        }
        currentTimeOnChannel = pulse->start() + pulse->duration();
      } else if (inst->isEnabled() && inst->isComposite()) {
        size_t nextCompositeStartTime = 0;
        for (const auto& kv : io_channel2times) {
          nextCompositeStartTime = kv.second > nextCompositeStartTime ? kv.second  : nextCompositeStartTime;
        }
        auto compositeInstPtr = std::dynamic_pointer_cast<xacc::CompositeInstruction>(inst);
        if (!compositeInstPtr) {
            xacc::error("Invalid instruction in pulse program.");
        }
        processComposite(compositeInstPtr, nextCompositeStartTime, io_channel2times);
      }
    } 
  }
}
namespace xacc {
namespace quantum {

void PulseScheduler::schedule(std::shared_ptr<CompositeInstruction> program) {

  // Remember that sub-composites have timings relative to each other internally
  std::map<std::string, std::size_t> channel2times;
  // Run the recursive scheduler, starting at this root composite at time 0:
  processComposite(program, 0, channel2times);
}

}
}
