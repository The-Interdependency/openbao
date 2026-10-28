# Resource-run invariant

> **Resource scarcity requires contemplation BEFORE a compute run begins. Once begun, let it finish. If there is doubt you can finish it, do not start it.**

This is binding execution doctrine.

Before launching a compute run, inspect or estimate the resources that can determine whether the run can reach its natural terminal condition: wall time where externally constrained, CPU, memory, disk, battery/power, network availability, quotas, API/tool usage limits, process/session durability, and any other relevant scarce resource.

If there is material doubt that the available resources can sustain the run, do not start it. First reduce the job, stage or checkpoint it, move it to a durable environment, acquire sufficient resources, or leave the run `hmmm`.

Once a run begins, allow it to reach its natural terminal condition: successful completion, deterministic computational failure, or explicit authorized cancellation. Do not terminate a healthy computation because an arbitrary wall-clock budget was introduced merely to make the work "bounded," "falsifiable," or convenient to supervise.

A runtime or resource ceiling may be a scientific stopping rule only when that resource quantity is itself part of the hypothesis, acceptance criterion, safety boundary, or an actual externally imposed hard limit. Such a ceiling must be justified and fixed before launch. Do not manufacture one by habit.

If an unforeseen real resource emergency arises during execution—such as imminent power loss, memory exhaustion, storage exhaustion, a hard account/quota limit, or an external safety condition—preserve state and evidence where possible, then stop only as necessary. Record the interruption and its reason; do not reinterpret it as a scientific outcome unless the preregistered claim made that resource boundary load-bearing.

`hmmm`: uncertainty about whether the run can finish belongs before launch, not halfway through a healthy computation.
