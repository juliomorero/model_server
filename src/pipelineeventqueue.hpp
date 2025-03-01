//*****************************************************************************
// Copyright 2021 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//*****************************************************************************
#pragma once

#include <utility>

#include "session_id.hpp"
#include "threadsafequeue.hpp"

namespace ovms {

class Node;

using NodeSessionKeyPair = std::pair<std::reference_wrapper<Node>, session_key_t>;
using PipelineEventQueue = ThreadSafeQueue<NodeSessionKeyPair>;
}  // namespace ovms
