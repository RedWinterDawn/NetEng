# Plan for Chicago

## Aim 1: allow turn down of Level3 without impacting reachability.

**Issue today**: asr1k2.ord has no other reachability than via Level3 (it does not receive routes from asr1k.ord). BR1 does not accept full routes from both asr1k.ord and asr1k2.ord and so there are destinations that may be black-holed without the Level3 transit.

* asr1k.ord + asr1k2.ord exchange full routes, such that Comcast and HE transits can be used fully (we can turn down Level3 without having issues).
	* We will stop filtering Comcast to only Comcast customer routes - since this gives us more options.
* Move br1 to having a default route only - such that we can avoid the issues of cache table size.
 * May originate more specifics of the global table if we think that there is a risk on the inter-site asr1k.ord-br1 and asr1k2.ord-br1 being overloaded.
 	* asr1k.ord - [Graphite](http://graphite.devops.jive.com/S/L)
 	* *Need to check for asr1k2.ord*.

* Ordered changes:
  * ```asr1k.ord/10_ibgp-filter-remove```
  * ```asr1k2.ord/10_ibgp-filter-remove```
  * *At this stage, asr1k.ord and asr1k2.ord have full routes from each other, and can use each other's transit connections - bestpath selection will be based on existing policy. Currently all local-prefs other than for specific Comcast routes are 100, so will be based on usual AS_PATH etc. rules*
  * ```asr1k2.ord/15_br1-route-maps```
  * ```asr1k2.ord/16_stage-bgp-config```
  * ```asr1k2.ord/20_remove-br1-peer```
  * *BR1 will now be routing according to the static routes (default plus more specifics) that it has plus the asr1k.ord BGP more-specifics. All traffic will hit asr1k.ord*.
  * ```asr1k2.ord/20_add-br1-peer```
  * *Re-established BGP peer, with solely a default route - traffic on BR1 will still follow the static default*.
  * ```asr1k.ord/15_br1-route-maps```
  * ```asr1k.ord/16_stage-bgp-config```
  * ```asr1k.ord/20_remove-br1-peer```
  * **BR1 will now route all traffic according to the static default + statically configured more specifics*
  * ```br1/25_increase-default-distance```
  * *BR1 will now route according to the BGP routes it has, plus the static more specifics*.
  * ```br1/30_static-route-cleanup```
  * *We may want to remove these routes at a later window, required for full resilience such that we can route without asr1k(2).ord. Verifying that the above works as expected is prudent before these changes.*

  