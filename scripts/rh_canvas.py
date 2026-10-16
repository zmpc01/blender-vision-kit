"""
rh_canvas.py — RH-canvas mocap clips + director statues for the kit
(polyhaven.py class: one file, two operating modes).

  VISION-KIT VENDOR (session 20): copied from mainline blender-agent-kit
  s38/s39 (b7c675d..6943ab5 lineage) — upstream-of-record for this file.
  Variant deltas: UA string only (intentionally zero code drift — the
  s39 hardening: channel-match bind guard, registry fingerprint,
  fake-user hygiene — is INCLUDED by the copy). The library data source
  (beulahkemp/RH-canvas-*) went dark 2026-10-16; tests run against the
  local fixture library (tests/rh_fixture_lib.py) or skip loudly.

  HOST-side  (no bpy — plain python3 or inside Blender):
    catalog      browse: --kind categories|animations|characters|models
                 (categories = the 19-code discovery list with counts);
                 animation rows carry consumer tags when present
                 (elevated_root_motion / static_pose — s39 full walk)
    fetch        sha256-verified CDN downloads into a cache dir
  BLENDER-side (via blrun.sh --background --python scripts/rh_canvas.py --):
    import-clip     FBX clip -> armature + action (scene range auto-set)
    mannequin       procedural capsule body skinned to the Mixamo rig
    bind            assign a clip action to an armature (never the mesh)
    import-statue   static director GLTF (meters, Z-up, feet-at-0 verified)

Library discovery is PATH-BASED (crowd-plugin precedent — data is never
vendored into the kit): --library DIR or env RH_CANVAS_LIB pointing at
(or containing, or sibling-of) clones named RH-canvas-animations /
RH-canvas-characters. Missing repos fail closed with the clone command.

Sources: github.com/beulahkemp/RH-canvas-animations (2,137 mocap FBX rows,
id-dedup -> 2,032 unique; 19 categories) + RH-canvas-characters (667
9-facet character presets; 99 static director GLTF statues, ~1.06 GB).
Ground truth: RH-RECON-1 (/home/z/rh_recon/REPORT.md — 28 binaries
live-probed on Blender 5.2.2) + REVIEW-RH-1b (mannequin/bind/round-trip
verified). Cache: env RH_CANVAS_CACHE else /home/z/rh_canvas_cache
(NEVER inside the clones — keeps them clean).

THE PLACEMENT LAW (read before moving anything):
  Place the ARMATURE, never the skinned mesh; translate/snap_z the
  armature BEFORE building the mannequin (rest feet z~=0.03); moving the
  mesh after binding breaks the bind.

The 9 laws (details in docs/rh_canvas.md):
  1. SCALE LAW    the FBX importer lands meters/Z-up via object scale
                  (0.01,0.01,0.01) + rotation X~=+90deg — KEEP that
                  state, NEVER transform_apply (see law 5).
  2. PLACEMENT    the law above (place/move/snap the ARMATURE first,
                  then build the mannequin at the spot).
  3. FRAME RANGE  read action.frame_range, NOT the scene's (the FBX
                  importer leaves the scene at 1..250). import-clip and
                  bind AUTO-SET scene.frame_start/end from the action
                  (export_frame_range=True clips to the scene range).
  4. FPS 30       every clip is 30 fps; import-clip/bind set
                  scene.render.fps=30 (glTF timing = frame/fps).
  5. CM-FCURVES   hips location fcurve values are RAW CENTIMETERS
                  (run clip peaks ~290 = 2.90 m); the 0.01 object scale
                  carries the conversion — never pre-scale or bake it.
  6. VERIFY       fetch law: cache hit -> size+sha256 -> mismatch
                  deletes + re-fetches; a fresh download STREAMS to a
                  .part temp file and verifies BEFORE os.replace (no RAM
                  buffers; statues up to 74.5 MB). sha256 for BOTH
                  manifests (the characters repo's own tool skips it —
                  do not inherit the bug).
  7. ID STRINGS   ids are STRINGS in both manifests — coerce with
                  str() everywhere ("2846" not 2846).
  8. SPAN         the T-pose span metric is |LeftHand.head -
                  RightHand.head| (wrist-to-wrist, ~1.476 m), NOT the
                  knuckle span (~1.73 m).
  9. >4 INFLUENCE ARMATURE_AUTO skinning gives some verts >4 bone
                  influences; the glTF exporter caps at 4 (cosmetic
                  weight loss, not an error — fingers lose a little).

Non-goals (v2 spec): no general retarget engine, no statue auto-rigging,
no decimation pipeline, no portrait VLM casting, no bulk mirroring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------- #
#  Constants / config
# --------------------------------------------------------------------------- #
ANIM_REPO = "RH-canvas-animations"
CHAR_REPO = "RH-canvas-characters"
ANIM_CLONE_CMD = "git clone https://github.com/beulahkemp/RH-canvas-animations.git"
CHAR_CLONE_CMD = "git clone https://github.com/beulahkemp/RH-canvas-characters.git"

# Kit UA (polyhaven.py convention). CDN is public/no-auth; a unique UA is
# good hygiene. Override via env if you fork this.
USER_AGENT = os.environ.get(
    "RH_CANVAS_UA",
    "blender-vision-kit/0.1 (+https://github.com/zmpc01/blender-vision-kit)")

# Default cache: env RH_CANVAS_CACHE else /home/z/rh_canvas_cache — NOT
# inside the clones (keeps them clean; v1 spec 1.2).
DEFAULT_CACHE = os.environ.get("RH_CANVAS_CACHE", "/home/z/rh_canvas_cache")

MIXAMO_PREFIX = "mixamorig:"
MIXAMO_BONE_COUNT = 65          # one identical rig across every sampled clip
FBX_FPS = 30                    # every clip is 30 fps (recon PART 2)

# Browse-time consumer tags, derived from the s39 FULL-library walk
# (tests/rh_fullwalk.py: all 2,032 clips imported + bound + posed; 150 s,
# 2,032/2,032 PASS). Regenerate these sets by re-running the walk if the
# library snapshot ever updates.
#   elevated_root_motion: head leaves the [floor-0.3 m, 2.4 m] band --
#     the climb/hang/leap/jump-down/backflip family. The clip APPLIES
#     fine; pair it with set geometry (a wall / ladder / platform /
#     ledge) or the actor visibly rises into the air.
#   static_pose: posed but near-zero within-clip motion (< 5 mm) -- the
#     pose-hold class (basic idle poses, prone casualties). Intended
#     behavior for a POSE library, not a defect.
ELEVATED_ROOT_MOTION = frozenset((
    "2206", "4126", "4069", "4125", "4117", "4067", "2471", "3039",
    "3054", "3071", "3085", "3086", "3090", "3094", "3095", "3100",
    "3102", "3104", "3105", "3109", "3110", "3111", "3113", "3116",
    "3342", "3385", "3401", "3402", "3419", "3670", "3683", "3750",
    "3768", "3917", "3919", "3923", "3925",
))
STATIC_POSE = frozenset((
    "2147", "2148", "4165", "2380", "2417", "2625", "2737", "2793",
    "2821", "3276", "3374", "3377", "3387", "3388", "3505", "3592",
    "3593", "3729", "3734", "3782", "3789", "3896", "4035", "4057",
    "4063",
))

# Per-clip frame counts (s39 full walk) as a compact "id:frames" string
# — parsed lazily into CLIP_FRAMES. Distribution: min 7, p25 39, median
# 69, p75 125, p95 343, max 1401 frames @30fps (the LONG tail is real:
# 59% of clips exceed 57 frames; "17-57" in early docs was a sampled-
# clip artifact, not a library bound). Browse-time duration for timeline
# planning (the s39-U1 top ask); regenerate via tests/rh_fullwalk.py if
# the library snapshot updates.
_CLIP_FRAMES_SRC = """2034:104,2035:151,2036:44,2037:528,2038:286,2039:144,2040:138,2041:152,2042:151,2043:303,2044:225,2045:45,2046:122,2047:36,2048:201,2049:161,2050:37,2051:201,2052:211,2053:61,2054:34,2055:222,2056:50,2057:61,2058:19,2059:96,2060:112,2061:115,2062:44,2063:139,2064:428,2065:160,2066:141,2067:163,2068:122,2069:73,2070:41,2071:41,2072:60,2073:201,2074:36,2075:149,2076:25,2077:25,2078:47,2079:122,2080:184,2081:101,2082:90,2083:209,2084:131,2085:106,2086:121,2087:121,2088:155,2089:116,2090:80,2091:128,2092:142,2093:102,2094:79,2095:350,2096:71,2097:61,2098:32,2099:181,2100:175,2101:94,2102:76,2103:111,2104:100,2105:192,2106:107,2107:129,2108:104,2109:81,2110:232,2111:90,2112:107,2113:130,2114:80,2115:82,2116:66,2117:67,2118:70,2119:69,2120:54,2121:55,2122:54,2123:50,2124:48,2125:31,2126:50,2127:80,2128:260,2129:153,2130:23,2131:58,2132:19,2133:20,2134:61,2135:56,2136:28,2137:22,2138:281,2139:153,2140:46,2141:16,2142:19,2143:23,2144:22,2145:51,2146:36,2147:50,2148:51,2149:49,2150:1113,2151:768,2152:566,2153:896,2154:62,2155:193,2156:242,2157:37,2158:137,2159:161,2160:109,2161:64,2162:75,2163:51,2164:31,2165:147,2166:202,2167:62,2168:86,2169:26,2170:138,2171:49,2172:110,2173:111,2174:289,2175:106,2176:16,2177:147,2178:125,2179:595,2180:235,2181:55,2182:70,2183:71,2184:67,2185:459,2186:69,2187:74,2188:79,2189:69,2190:80,2191:372,2192:326,2193:457,2194:628,2195:392,2196:63,2197:648,2198:844,2199:570,2200:61,2201:61,2202:86,2203:82,2204:56,2205:101,2206:62,2207:51,2208:53,2209:164,2210:116,2211:595,2212:642,2213:786,2214:837,2215:464,2216:75,2217:742,2218:36,2219:480,2220:23,2221:46,2222:91,2223:244,2224:221,2225:71,2226:69,2227:83,2228:62,2229:655,2230:62,2231:76,2232:156,2233:60,2234:66,2235:156,2236:717,2237:54,2238:66,2239:366,2240:439,2241:213,2242:143,2243:102,2244:135,2245:157,2246:124,2247:90,2248:72,2249:483,2250:364,2251:509,2252:474,2253:184,2254:414,2255:360,2256:660,2257:518,2258:410,2259:461,2260:225,2261:319,2262:44,2263:33,2264:226,2265:284,2266:111,2267:144,2268:136,2358:50,2359:30,2360:50,2361:31,2362:30,2363:44,2364:39,2365:34,2366:44,2367:29,2368:29,2369:176,2370:166,2371:201,2372:44,2373:45,2374:21,2375:24,2376:39,2377:37,2378:37,2379:34,2380:154,2381:22,2382:97,2383:69,2384:69,2385:94,2386:78,2387:61,2388:71,2389:72,2390:96,2391:33,2392:33,2393:31,2394:21,2395:45,2396:42,2397:27,2398:28,2399:37,2400:38,2401:31,2402:21,2403:31,2404:24,2405:31,2406:39,2407:24,2408:31,2409:16,2410:72,2411:50,2412:24,2413:42,2414:162,2415:61,2416:52,2417:149,2418:36,2419:52,2420:42,2421:38,2422:37,2423:16,2424:31,2425:35,2426:101,2427:28,2428:28,2429:84,2430:89,2431:86,2432:115,2433:19,2434:24,2435:25,2436:111,2437:29,2438:23,2439:21,2440:23,2441:16,2442:20,2443:19,2444:88,2445:42,2446:124,2447:102,2448:34,2449:40,2450:25,2451:69,2452:24,2453:23,2454:37,2455:113,2456:46,2457:76,2458:61,2459:7,2460:7,2461:34,2462:93,2463:88,2464:75,2465:52,2466:58,2467:164,2468:151,2469:114,2470:96,2471:70,2472:37,2473:91,2474:115,2475:100,2476:207,2477:193,2478:9,2479:36,2480:26,2481:84,2482:31,2483:31,2484:73,2485:39,2486:39,2487:31,2488:31,2489:89,2490:64,2491:64,2492:31,2493:31,2494:31,2495:31,2496:31,2497:21,2498:17,2499:58,2500:52,2501:25,2502:38,2503:60,2504:63,2505:16,2506:16,2507:45,2508:60,2509:32,2510:44,2511:31,2512:59,2513:31,2514:108,2515:54,2516:64,2517:64,2518:94,2519:29,2520:54,2521:25,2522:46,2523:90,2524:100,2525:86,2526:56,2527:320,2528:74,2529:86,2530:46,2531:16,2532:16,2533:47,2534:16,2535:61,2536:31,2537:31,2538:87,2539:16,2540:16,2541:31,2542:31,2543:27,2544:36,2545:16,2546:16,2547:16,2548:16,2549:16,2550:16,2551:16,2552:52,2553:38,2554:60,2555:17,2556:18,2557:21,2558:19,2559:111,2560:69,2561:120,2562:70,2563:70,2564:94,2565:56,2566:61,2567:45,2568:61,2569:89,2570:106,2571:97,2572:174,2573:246,2574:84,2575:186,2576:107,2577:152,2578:42,2579:122,2580:31,2581:61,2582:44,2583:179,2584:250,2585:41,2586:36,2587:28,2588:62,2589:53,2590:31,2591:46,2592:36,2593:35,2594:74,2595:151,2596:81,2597:79,2598:74,2599:16,2600:19,2601:17,2602:16,2603:42,2604:43,2605:45,2606:39,2607:32,2608:19,2609:37,2610:67,2611:55,2612:35,2613:70,2614:83,2615:19,2616:42,2617:56,2618:79,2619:31,2620:41,2621:36,2622:18,2623:78,2624:99,2625:121,2626:62,2627:81,2628:47,2629:73,2630:31,2631:61,2632:93,2633:46,2634:50,2635:50,2636:56,2637:23,2638:35,2639:24,2640:16,2641:25,2642:51,2643:43,2644:58,2645:21,2646:21,2647:20,2648:35,2649:36,2650:39,2651:151,2652:91,2653:56,2654:51,2655:56,2656:91,2657:80,2658:339,2659:236,2660:121,2661:134,2662:134,2663:198,2664:198,2665:35,2666:76,2667:51,2668:145,2669:139,2670:116,2671:46,2672:93,2673:39,2674:86,2675:76,2676:96,2677:71,2678:61,2679:41,2680:107,2681:56,2682:21,2683:43,2684:30,2685:44,2686:22,2687:12,2688:66,2689:28,2690:20,2691:18,2692:25,2693:27,2694:21,2695:16,2696:228,2697:112,2698:114,2699:34,2700:20,2701:36,2702:15,2703:16,2704:37,2705:46,2706:145,2707:61,2708:39,2709:23,2710:40,2711:53,2712:65,2713:56,2714:26,2715:62,2716:21,2717:25,2718:36,2719:42,2720:23,2721:34,2722:41,2723:74,2724:67,2725:73,2726:49,2727:32,2728:54,2729:96,2730:110,2731:157,2732:144,2733:164,2734:99,2735:137,2736:40,2737:16,2738:42,2739:16,2740:71,2741:30,2742:26,2743:22,2744:25,2745:24,2746:25,2747:72,2748:111,2749:43,2750:21,2751:19,2752:30,2753:20,2754:90,2755:37,2756:107,2757:18,2758:77,2759:74,2760:74,2761:16,2762:21,2763:40,2764:22,2765:17,2766:118,2767:22,2768:35,2769:227,2770:53,2771:51,2772:70,2773:46,2774:29,2775:106,2776:97,2777:116,2778:83,2779:141,2780:127,2781:500,2782:120,2783:223,2784:55,2785:47,2786:87,2787:31,2788:57,2789:51,2790:50,2791:366,2792:58,2793:154,2794:181,2795:301,2796:116,2797:60,2798:191,2799:134,2800:100,2801:76,2802:76,2803:187,2804:31,2805:57,2806:53,2807:345,2808:81,2809:85,2810:538,2811:89,2812:101,2813:301,2814:149,2815:120,2816:276,2817:301,2818:299,2819:99,2820:76,2821:61,2822:101,2823:76,2824:292,2825:27,2826:48,2827:60,2828:91,2829:31,2830:111,2831:50,2832:57,2833:44,2834:56,2835:46,2836:46,2837:50,2838:49,2839:50,2840:21,2841:31,2842:211,2843:21,2844:21,2845:21,2846:17,2847:23,2848:24,2849:86,2850:23,2851:13,2852:19,2853:109,2854:74,2855:21,2856:29,2857:45,2858:45,2859:29,2860:48,2861:76,2862:201,2863:32,2864:85,2865:36,2866:35,2867:29,2868:42,2869:37,2870:89,2871:29,2872:84,2873:121,2874:36,2875:51,2876:32,2877:29,2878:29,2879:32,2880:36,2881:36,2882:32,2883:29,2884:29,2885:36,2886:50,2887:51,2888:50,2889:29,2890:64,2891:522,2892:39,2893:76,2894:69,2895:46,2896:37,2897:26,2898:43,2899:38,2900:44,2901:41,2902:43,2903:298,2904:439,2905:53,2906:72,2907:119,2908:121,2909:112,2910:149,2911:73,2912:75,2913:51,2914:34,2915:34,2916:32,2917:32,2918:23,2919:36,2920:66,2921:23,2922:179,2923:40,2924:69,2925:40,2926:28,2927:85,2928:21,2929:20,2930:31,2931:28,2932:28,2933:33,2934:34,2935:74,2936:47,2937:38,2938:39,2939:25,2940:27,2941:38,2942:37,2943:33,2944:33,2945:33,2946:139,2947:30,2948:17,2949:377,2950:32,2951:78,2952:72,2953:30,2954:39,2955:31,2956:36,2957:42,2958:19,2959:19,2960:20,2961:32,2962:18,2963:16,2964:17,2965:32,2966:37,2967:35,2968:34,2969:38,2970:41,2971:57,2972:17,2973:18,2974:32,2975:19,2976:38,2977:37,2978:109,2979:76,2980:110,2981:179,2982:108,2983:75,2984:59,2985:45,2986:37,2987:33,2988:47,2989:420,2990:38,2991:17,2992:24,2993:38,2994:37,2995:40,2996:37,2997:20,2998:39,2999:38,3000:32,3001:23,3002:56,3003:22,3004:23,3005:45,3006:81,3007:26,3008:44,3009:24,3010:37,3011:52,3012:31,3013:46,3014:36,3015:36,3016:18,3017:33,3018:63,3019:18,3020:38,3021:40,3022:45,3023:45,3024:63,3025:41,3026:52,3027:39,3028:47,3029:57,3030:46,3031:44,3032:60,3033:45,3034:46,3035:52,3036:98,3037:72,3038:119,3039:37,3040:80,3041:46,3042:46,3043:31,3044:33,3045:27,3046:103,3047:41,3048:51,3049:61,3050:72,3051:71,3052:151,3053:74,3054:93,3055:98,3056:106,3057:8,3058:26,3059:72,3060:51,3061:66,3062:79,3063:39,3064:58,3065:28,3066:43,3067:62,3068:56,3069:74,3070:68,3071:116,3072:71,3073:34,3074:64,3075:64,3076:42,3077:43,3078:35,3079:19,3080:59,3081:52,3082:75,3083:66,3084:62,3085:73,3086:65,3087:70,3088:42,3089:64,3090:80,3091:73,3092:38,3093:107,3094:74,3095:60,3096:79,3097:116,3098:48,3099:33,3100:35,3101:46,3102:51,3103:51,3104:40,3105:28,3106:29,3107:79,3108:95,3109:61,3110:24,3111:61,3112:140,3113:116,3114:79,3115:142,3116:66,3117:43,3118:26,3119:36,3120:27,3121:74,3122:27,3123:72,3124:29,3125:32,3126:29,3127:31,3128:124,3129:36,3130:77,3131:36,3132:33,3133:34,3134:91,3135:47,3136:39,3137:52,3138:30,3139:54,3140:56,3141:21,3142:18,3143:16,3144:268,3145:96,3146:44,3147:56,3148:26,3149:31,3150:25,3151:60,3152:26,3153:89,3154:69,3155:69,3156:62,3157:68,3158:64,3159:16,3160:31,3161:40,3162:33,3163:26,3164:31,3165:128,3166:71,3167:126,3168:84,3169:105,3170:99,3171:80,3172:201,3173:51,3174:136,3175:68,3176:176,3177:74,3178:62,3179:69,3180:151,3181:62,3182:106,3183:106,3184:218,3185:218,3186:51,3187:49,3188:46,3189:49,3190:41,3191:81,3192:33,3193:28,3194:31,3195:25,3196:27,3197:58,3198:40,3199:60,3200:88,3201:65,3202:65,3203:110,3204:72,3205:100,3206:69,3207:81,3208:69,3209:49,3210:211,3211:66,3212:104,3213:56,3214:61,3215:31,3216:50,3217:77,3218:228,3219:41,3220:37,3221:41,3222:112,3223:103,3224:112,3225:106,3226:149,3227:71,3228:75,3229:69,3230:67,3231:64,3232:50,3233:67,3234:32,3235:66,3236:67,3237:31,3238:53,3239:67,3240:68,3241:65,3242:32,3243:201,3244:141,3245:141,3246:129,3247:33,3248:33,3249:29,3250:25,3251:24,3252:26,3253:41,3254:36,3255:40,3256:46,3257:49,3258:51,3259:47,3260:40,3261:50,3262:48,3263:46,3264:37,3265:38,3266:38,3267:36,3268:29,3269:33,3270:31,3271:38,3272:104,3273:75,3274:191,3275:144,3276:30,3277:151,3278:46,3279:65,3280:67,3281:45,3282:34,3283:149,3284:67,3285:40,3286:72,3287:35,3288:38,3289:51,3290:114,3291:116,3292:532,3293:57,3294:85,3295:66,3296:68,3297:139,3298:42,3299:92,3300:93,3301:123,3302:50,3303:104,3304:145,3305:104,3306:156,3307:91,3308:67,3309:75,3310:42,3311:100,3312:53,3313:61,3314:79,3315:88,3316:121,3317:31,3318:39,3319:53,3320:85,3321:32,3322:99,3323:90,3324:24,3325:46,3326:39,3327:44,3328:38,3329:27,3330:25,3331:29,3332:26,3333:26,3334:55,3335:73,3336:61,3337:109,3338:171,3339:87,3340:71,3341:74,3342:62,3343:20,3344:38,3345:46,3346:20,3347:31,3348:31,3349:31,3350:55,3351:199,3352:206,3353:91,3354:47,3355:26,3356:51,3357:32,3358:91,3359:39,3360:41,3361:39,3362:39,3363:46,3364:46,3365:48,3366:46,3367:55,3368:55,3369:34,3370:20,3371:78,3372:78,3373:143,3374:129,3375:207,3376:59,3377:141,3378:118,3379:58,3380:46,3381:34,3382:36,3383:34,3384:39,3385:66,3386:107,3387:69,3388:69,3389:83,3390:84,3391:39,3392:84,3393:35,3394:94,3395:71,3396:78,3397:28,3398:51,3399:29,3400:31,3401:35,3402:57,3403:59,3404:69,3405:32,3406:35,3407:32,3408:32,3409:39,3410:35,3411:35,3412:33,3413:36,3414:38,3415:35,3416:40,3417:35,3418:35,3419:55,3420:196,3421:181,3422:151,3423:186,3424:42,3425:47,3426:102,3427:177,3428:120,3429:384,3430:99,3431:28,3432:70,3433:127,3434:58,3435:65,3436:20,3437:56,3438:102,3439:220,3440:101,3441:41,3442:36,3443:83,3444:22,3445:23,3446:26,3447:23,3448:25,3449:25,3450:26,3451:43,3452:72,3453:49,3454:39,3455:107,3456:74,3457:36,3458:115,3459:180,3460:74,3461:64,3462:70,3463:51,3464:57,3465:73,3466:103,3467:79,3468:71,3469:151,3470:137,3471:95,3472:77,3473:99,3474:94,3475:633,3476:114,3477:164,3478:121,3479:1121,3480:313,3481:46,3482:60,3483:276,3484:157,3485:118,3486:60,3487:95,3488:264,3489:258,3490:311,3491:207,3492:105,3493:521,3494:119,3495:100,3496:164,3497:44,3498:275,3499:175,3500:121,3501:51,3502:148,3503:300,3504:176,3505:91,3506:79,3507:86,3508:116,3509:83,3510:82,3511:95,3512:240,3513:107,3514:64,3515:39,3516:232,3517:101,3518:140,3519:103,3520:17,3521:98,3522:16,3523:118,3524:94,3525:118,3526:98,3527:47,3528:69,3529:34,3530:188,3531:322,3532:243,3533:200,3534:79,3535:117,3536:60,3537:31,3538:221,3539:133,3540:62,3541:177,3542:253,3543:368,3544:305,3545:261,3546:116,3547:160,3548:96,3549:107,3550:226,3551:87,3552:118,3553:39,3554:55,3555:33,3556:33,3557:87,3558:30,3559:30,3560:38,3561:148,3562:112,3563:158,3564:419,3565:431,3566:141,3567:557,3568:175,3569:228,3570:121,3571:32,3572:1118,3573:433,3574:151,3575:67,3576:267,3577:65,3578:645,3579:145,3580:69,3581:1401,3582:275,3583:73,3584:187,3585:301,3586:117,3587:293,3588:52,3589:120,3590:146,3591:93,3592:151,3593:151,3594:42,3595:37,3596:40,3597:181,3598:179,3599:46,3600:142,3601:217,3602:147,3603:288,3604:67,3605:168,3606:124,3607:269,3608:330,3609:24,3610:69,3611:143,3612:42,3613:47,3614:125,3615:33,3616:100,3617:489,3618:1166,3619:1130,3620:35,3621:34,3622:995,3623:68,3624:36,3625:85,3626:414,3627:271,3628:330,3629:186,3630:79,3631:41,3632:188,3633:708,3634:311,3635:146,3636:66,3637:154,3638:180,3639:60,3640:142,3641:130,3642:126,3643:68,3644:24,3645:71,3646:71,3647:43,3648:45,3649:56,3650:28,3651:91,3652:89,3653:34,3654:189,3655:361,3656:281,3657:122,3658:191,3659:168,3660:90,3661:576,3662:301,3663:123,3664:147,3665:142,3666:144,3667:151,3668:37,3669:36,3670:67,3671:58,3672:50,3673:401,3674:339,3675:57,3676:55,3677:79,3678:109,3679:67,3680:81,3681:63,3682:309,3683:73,3684:93,3685:176,3686:114,3687:119,3688:156,3689:121,3690:121,3691:32,3692:96,3693:86,3694:98,3695:109,3696:84,3697:156,3698:60,3699:267,3700:103,3701:85,3702:67,3703:71,3704:31,3705:191,3706:89,3707:169,3708:184,3709:257,3710:203,3711:99,3712:365,3713:373,3714:294,3715:122,3716:251,3717:59,3718:65,3719:94,3720:121,3721:246,3722:213,3723:113,3724:213,3725:113,3726:132,3727:56,3728:279,3729:145,3730:29,3731:151,3732:242,3733:51,3734:44,3735:60,3736:65,3737:96,3738:131,3739:105,3740:123,3741:49,3742:61,3743:37,3744:53,3745:91,3746:279,3747:22,3748:48,3749:48,3750:117,3751:41,3752:139,3753:126,3754:134,3755:150,3756:148,3757:343,3758:249,3759:46,3760:140,3761:60,3762:72,3763:62,3764:151,3765:457,3766:51,3767:104,3768:121,3769:132,3770:71,3771:79,3772:104,3773:63,3774:186,3775:259,3776:251,3777:105,3778:114,3779:84,3780:101,3781:251,3782:90,3783:126,3784:121,3785:126,3786:101,3787:106,3788:251,3789:130,3790:179,3791:144,3792:140,3793:193,3794:91,3795:1350,3796:1323,3797:309,3798:104,3799:144,3800:104,3801:69,3802:183,3803:196,3804:171,3805:228,3806:123,3807:176,3808:116,3809:99,3810:115,3811:106,3812:129,3813:686,3814:188,3815:135,3816:1216,3817:142,3818:238,3819:97,3820:101,3821:292,3822:141,3823:284,3824:85,3825:312,3826:81,3827:140,3828:57,3829:343,3830:99,3831:173,3832:51,3833:111,3834:260,3835:306,3836:131,3837:150,3838:511,3839:479,3840:148,3841:762,3842:372,3843:455,3844:324,3845:547,3846:560,3847:489,3848:822,3849:471,3850:30,3851:520,3852:558,3853:36,3854:266,3870:123,3871:130,3872:83,3873:211,3874:142,3875:78,3876:214,3877:160,3878:18,3879:145,3880:232,3881:84,3882:99,3883:14,3884:52,3885:72,3886:26,3887:174,3888:69,3889:37,3890:261,3891:168,3892:251,3893:91,3894:321,3895:349,3896:59,3897:264,3898:20,3899:137,3900:39,3901:22,3902:27,3903:78,3904:196,3905:47,3906:21,3907:20,3908:37,3909:25,3910:42,3911:23,3912:69,3913:63,3914:45,3915:136,3916:80,3917:181,3918:84,3919:81,3920:80,3921:76,3922:89,3923:105,3924:91,3925:57,3926:43,3927:443,3928:81,3929:125,3930:88,3931:102,3932:225,3933:69,3934:93,3935:68,3936:90,3937:34,3938:67,3939:76,3940:112,3941:144,3942:66,3943:92,3944:84,3945:66,3946:61,3947:61,3948:81,3949:42,3950:161,3951:228,3952:149,3953:166,3954:325,3955:20,3956:77,3957:464,3958:237,3959:318,3960:312,3961:46,3962:409,3963:386,3964:355,3965:89,3966:231,3967:53,3968:218,3969:68,3970:180,3971:37,3972:158,3973:110,3974:151,3975:1268,3976:192,3977:194,3978:169,3979:81,3980:135,3981:137,3982:93,3983:66,3984:34,3985:264,3986:169,3987:1338,3988:189,3989:98,3990:121,3991:274,3992:346,3993:408,3994:214,3995:179,3996:187,3997:59,3998:138,3999:58,4000:55,4001:198,4002:328,4003:151,4004:88,4005:77,4006:61,4007:135,4008:91,4009:126,4010:133,4011:625,4012:77,4013:57,4014:236,4015:53,4016:86,4017:91,4018:163,4019:115,4020:17,4021:60,4022:101,4023:80,4024:60,4025:236,4026:99,4027:111,4028:78,4029:74,4030:83,4031:114,4032:83,4033:284,4034:117,4035:36,4036:131,4037:189,4038:99,4039:135,4040:56,4041:68,4042:195,4043:200,4044:114,4045:81,4046:62,4047:191,4048:55,4049:52,4050:26,4051:53,4052:55,4053:529,4054:151,4055:207,4056:64,4057:36,4058:211,4059:119,4060:495,4061:134,4062:176,4063:126,4064:106,4065:201,4066:136,4067:76,4068:228,4069:201,4070:107,4071:131,4072:174,4073:56,4074:100,4075:171,4076:64,4077:146,4078:82,4079:36,4080:123,4081:41,4082:30,4083:31,4084:35,4085:37,4086:45,4087:49,4088:49,4089:43,4090:126,4091:155,4092:58,4093:75,4094:67,4095:79,4096:75,4097:171,4098:14,4099:78,4100:106,4101:166,4102:145,4103:150,4104:85,4105:69,4106:76,4107:80,4108:48,4109:73,4110:342,4111:139,4112:247,4113:520,4114:401,4115:61,4116:22,4117:65,4118:55,4119:94,4120:79,4121:42,4122:50,4123:48,4124:51,4125:91,4126:69,4127:127,4128:37,4129:39,4130:204,4131:112,4132:109,4133:79,4134:112,4135:57,4136:92,4137:72,4138:111,4139:78,4140:110,4141:133,4142:136,4143:92,4144:101,4145:141,4146:120,4147:51,4148:56,4149:112,4150:117,4151:131,4152:243,4153:139,4154:81,4155:84,4156:99,4157:75,4158:76,4159:146,4160:85,4161:149,4162:169,4163:69,4164:12,4165:206,4166:25,4167:139,4168:163,4169:77"""
CLIP_FRAMES: dict[str, int] = {}


def _load_clip_frames() -> dict[str, int]:
    if not CLIP_FRAMES and _CLIP_FRAMES_SRC:
        for pair in _CLIP_FRAMES_SRC.split(","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                CLIP_FRAMES[k] = int(v)
    return CLIP_FRAMES


def clip_tags(anim_id: str) -> list[str]:
    """Browse-time consumer tags for a clip id (see the sets above)."""
    aid = str(anim_id)
    tags = []
    if aid in ELEVATED_ROOT_MOTION:
        tags.append("elevated_root_motion")
    if aid in STATIC_POSE:
        tags.append("static_pose")
    return tags


def clip_frames(anim_id: str) -> int | None:
    """Frame count at browse time (s39 full-walk table); None unknown."""
    return _load_clip_frames().get(str(anim_id))


# Capsule radii (metres) for the mannequin build — REVIEW-RH-1b verified:
# 22 segments from data.bones REST positions -> 616 verts -> 65 groups,
# 0 zero-weight verts, rest bbox 1.695 x 0.388 x 1.801 m.
CAPSULE_RADII = {
    "Hips": 0.13, "Spine": 0.11, "Spine1": 0.13, "Spine2": 0.13,
    "Neck": 0.055, "Head": 0.11,
    "LeftShoulder": 0.05, "RightShoulder": 0.05,
    "LeftArm": 0.045, "LeftForeArm": 0.04, "LeftHand": 0.04,
    "RightArm": 0.045, "RightForeArm": 0.04, "RightHand": 0.04,
    "LeftUpLeg": 0.075, "LeftLeg": 0.055, "LeftFoot": 0.04, "LeftToeBase": 0.035,
    "RightUpLeg": 0.075, "RightLeg": 0.055, "RightFoot": 0.04, "RightToeBase": 0.035,
}


class RHRefused(Exception):
    """Teacher-grade refusal (fail-closed): the message names the exact
    problem AND the fix. The CLI turns this into '[rh] REFUSED: ...' +
    exit 2 — never a traceback."""


# --------------------------------------------------------------------------- #
#  Library discovery (host-side, no bpy)
# --------------------------------------------------------------------------- #
def _looks_like_animations(d: str) -> bool:
    return os.path.isfile(os.path.join(d, "assets-manifest.json")) \
        and os.path.isfile(os.path.join(d, "data", "animations.jsonl"))


def _looks_like_characters(d: str) -> bool:
    return os.path.isfile(os.path.join(d, "director-gltf-manifest.json")) \
        and os.path.isfile(os.path.join(d, "data", "characters.jsonl"))


def discover_libraries(explicit: str | None = None) -> dict:
    """Locate the RH-canvas clones. Returns
    {'animations': path|None, 'characters': path|None}.

    Search order for a base dir: the dir itself (when it IS a clone),
    <base>/<repo-name>, and the dir's parent's <repo-name> children —
    so --library can point at either clone, at their common parent, or
    at any sibling directory. When --library / RH_CANVAS_LIB is given it
    is AUTHORITATIVE (fail-closed: no silent fallback probes); otherwise
    the kit's parent dir, cwd and cwd's parent are auto-probed."""
    bases: list[str] = []
    pinned = explicit or os.environ.get("RH_CANVAS_LIB")
    if pinned:
        cands = [pinned]
    else:
        cands = [os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # kit parent
                 os.getcwd()]
    for cand in cands:
        if cand and os.path.isdir(cand):
            c = os.path.abspath(cand)
            if c not in bases:
                bases.append(c)
            parent = os.path.dirname(c)
            if parent and os.path.isdir(parent) and parent not in bases:
                bases.append(parent)

    found: dict = {}
    for base in bases:
        for repo, key, check in ((ANIM_REPO, "animations", _looks_like_animations),
                                 (CHAR_REPO, "characters", _looks_like_characters)):
            if key in found:
                continue
            probes = [base,
                      os.path.join(base, repo)]
            for p in probes:
                if os.path.isdir(p) and check(p):
                    found[key] = os.path.abspath(p)
                    break
    return found


def require_library(which: str, explicit: str | None = None) -> str:
    """Fail-closed library lookup. `which` in {'animations','characters'}."""
    libs = discover_libraries(explicit)
    path = libs.get(which)
    if path:
        return path
    repo = ANIM_REPO if which == "animations" else CHAR_REPO
    clone = ANIM_CLONE_CMD if which == "animations" else CHAR_CLONE_CMD
    other = ""
    if not libs.get("animations" if which == "characters" else "characters"):
        other_repo = CHAR_REPO if which == "animations" else ANIM_REPO
        other_clone = CHAR_CLONE_CMD if which == "animations" else ANIM_CLONE_CMD
        other = (f"\n  (the sibling repo {other_repo} is also absent; when "
                 f"you need it: {other_clone})")
    raise RHRefused(
        f"the {which} library repo {repo} was not found. Point --library "
        f"(or env RH_CANVAS_LIB) at the clone, its parent, or any sibling "
        f"dir — or clone it:\n    {clone}{other}")


# --------------------------------------------------------------------------- #
#  Catalog loading (host-side, no bpy, no network)
# --------------------------------------------------------------------------- #
def load_animations(explicit: str | None = None) -> list[dict]:
    """assets-manifest.json rows, id-deduped (2,137 -> 2,032; the pairs
    are exact duplicate rows — recon PART 1). ids coerced to STRINGS."""
    root = require_library("animations", explicit)
    with open(os.path.join(root, "assets-manifest.json"), encoding="utf-8") as f:
        rows = json.load(f)
    seen: dict[str, dict] = {}
    for e in rows:
        eid = str(e["id"])                                    # id-string law
        if eid in seen:
            continue
        seen[eid] = {
            "id": eid,
            "category": e["categoryCode"],
            "name": e["name"],                                # Chinese: display
            "nameEn": e.get("nameEn", ""),                    # search-hint only
            "size": e["size"],
            "sha256": e["sha256"],
            "url": e["url"],
        }
    return list(seen.values())


def load_categories(explicit: str | None = None) -> dict[str, dict]:
    """category_tree.json -> {code: {'name': ZH, 'nameEn': en}} (19 cats)."""
    root = require_library("animations", explicit)
    with open(os.path.join(root, "data", "category_tree.json"), encoding="utf-8") as f:
        tree = json.load(f)
    return {c["code"]: {"name": c["name"], "nameEn": c.get("nameEn", "").strip()}
            for c in tree}


def load_characters(explicit: str | None = None) -> list[dict]:
    """characters.jsonl -> 667 presets with a flattened 9-facet taxonomy."""
    root = require_library("characters", explicit)
    out = []
    with open(os.path.join(root, "data", "characters.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            facets = {k: v.get("optionCode", "")
                      for k, v in (r.get("attributes") or {}).items()}
            out.append({"id": str(r["id"]), "name": r["name"],
                        "facets": facets})
    return out


def load_facet_options(explicit: str | None = None) -> dict[str, list[str]]:
    """filter_options.json -> {facet: [option codes...]} (excludes 'all')."""
    root = require_library("characters", explicit)
    with open(os.path.join(root, "data", "filter_options.json"), encoding="utf-8") as f:
        fo = json.load(f)
    facets: dict[str, list[str]] = {}
    for group in fo.get("groups", []):
        for cat in group.get("categories", []):
            codes = [o["code"] for o in cat.get("options", [])
                     if o.get("code") and o["code"] != "all"]
            facets[cat["code"]] = codes
    return facets


def load_models(explicit: str | None = None) -> list[dict]:
    """director_models.json joined with director-gltf-manifest.json (1:1,
    all 99 carry sha256) -> model entries keyed by name/uuid/filename."""
    root = require_library("characters", explicit)
    with open(os.path.join(root, "data", "director_models.json"), encoding="utf-8") as f:
        groups = json.load(f)
    with open(os.path.join(root, "director-gltf-manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    by_url = {e["url"]: e for e in manifest}
    models = []
    for g in groups:
        for m in g.get("models", []):
            entry = by_url.get(m.get("url"))
            if entry is None:                                 # fail closed
                raise RHRefused(
                    f"director model {m.get('name')!r} has no "
                    f"director-gltf-manifest.json entry (URL {m.get('url')}) "
                    f"— the two files must stay 1:1; re-clone "
                    f"{CHAR_REPO}")
            models.append({
                "id": m["id"],
                "name": m["name"],
                "group": g["key"],
                "group_label": g.get("label", ""),
                "size": entry["size"],
                "sha256": entry["sha256"],
                "url": entry["url"],
                "filename": os.path.basename(
                    urllib.parse.urlsplit(entry["url"]).path),
            })
    return models


# --------------------------------------------------------------------------- #
#  Fetch (the verify law) — host-side
# --------------------------------------------------------------------------- #
def enc(url: str) -> str:
    """Percent-encode the path (verbatim from the repo's own
    tools/fetch_assets.py — good hygiene even though 0 current URLs are
    non-ASCII)."""
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (p.scheme, p.netloc, urllib.parse.quote(p.path), p.query, ""))


def _sha256_file(path: str, bufsize: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(bufsize), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify(path: str, size: int, sha256: str) -> bool:
    return os.path.getsize(path) == size and _sha256_file(path) == sha256


def fetch_verified(entry: dict, dest: str, label: str = "") -> str:
    """The VERIFY LAW (v2 spec delta 4, law 6).

    cache hit   -> size + sha256 check; mismatch = DELETE + re-fetch
                  (a poisoned/partial cache repairs itself).
    fresh       -> STREAM to '<dest>.part' in 1 MiB chunks (no RAM
                  buffers — statues go up to 74.5 MB), verify size+sha256
                  BEFORE os.replace into place. A bad download never
                  touches the cache path.

    Returns 'ok-cached' | 'ok' | 're-fetched(repaired)'. Idempotent."""
    label = label or os.path.basename(dest)
    if os.path.exists(dest):
        if _verify(dest, entry["size"], entry["sha256"]):
            return "ok-cached"
        os.remove(dest)                       # poisoned/partial -> repair
        status = "re-fetched(repaired)"
    else:
        status = "ok"
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    tmp = dest + ".part"
    req = urllib.request.Request(enc(entry["url"]),
                                 headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as fh:
            while True:
                chunk = r.read(1 << 20)       # stream: 1 MiB, low RAM
                if not chunk:
                    break
                fh.write(chunk)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    if not _verify(tmp, entry["size"], entry["sha256"]):
        os.remove(tmp)
        raise RHRefused(
            f"download of {label} from {entry['url']} FAILED verification "
            f"(expected size {entry['size']}, sha256 "
            f"{entry['sha256'][:16]}…). The temp file was discarded — the "
            f"cache is NOT poisoned. Re-run; if it persists, the CDN copy "
            f"changed and the manifest is stale.")
    os.replace(tmp, dest)
    return status


def animation_cache_path(cache: str, anim: dict) -> str:
    return os.path.join(cache, "animations", anim["category"],
                        f"{anim['id']}.fbx")


def model_cache_path(cache: str, model: dict) -> str:
    return os.path.join(cache, "models", model["filename"])


def _find_animation(anim_id: str, explicit=None) -> dict | None:
    for a in load_animations(explicit):
        if a["id"] == str(anim_id):
            return a
    return None


def _find_model(key: str, explicit=None) -> dict | None:
    key = str(key)
    for m in load_models(explicit):
        if key in (m["name"], m["id"], m["filename"]):
            return m
    return None


def fetch_ids(ids: list[str], cache: str | None = None,
              explicit_lib: str | None = None) -> list[dict]:
    """Fetch animation clips and/or director statues by id (animations)
    or name/uuid/filename (models). Idempotent, sha256-verified."""
    cache = cache or DEFAULT_CACHE
    results = []
    for raw in ids:
        key = str(raw).strip()
        anim = _find_animation(key, explicit_lib)
        if anim is not None:
            dest = animation_cache_path(cache, anim)
            status = fetch_verified(anim, dest, f"animation {anim['id']}")
            results.append({"id": anim["id"], "kind": "animation",
                            "name": anim["name"], "status": status,
                            "dest": dest})
            continue
        model = _find_model(key, explicit_lib)
        if model is not None:
            dest = model_cache_path(cache, model)
            status = fetch_verified(model, dest, f"model {model['name']}")
            results.append({"id": model["name"], "kind": "model",
                            "name": model["name"], "status": status,
                            "dest": dest})
            continue
        raise RHRefused(
            f"id {key!r} is neither an animation id (see `catalog --kind "
            f"animations`) nor a director model name/uuid (see `catalog "
            f"--kind models`). Nothing was fetched.")
    return results


def ensure_animation(anim_id: str, cache: str | None = None,
                     explicit_lib: str | None = None) -> str:
    """fetch-if-missing; returns the local FBX path (idempotent)."""
    anim = _find_animation(anim_id, explicit_lib)
    if anim is None:
        raise RHRefused(
            f"animation id {anim_id!r} not in the catalog (ids are STRINGS; "
            f"see `catalog --kind animations`).")
    dest = animation_cache_path(cache or DEFAULT_CACHE, anim)
    fetch_verified(anim, dest, f"animation {anim['id']}")
    return dest


def ensure_model(name: str, cache: str | None = None,
                 explicit_lib: str | None = None) -> str:
    model = _find_model(name, explicit_lib)
    if model is None:
        raise RHRefused(
            f"director model {name!r} not found (match by name, uuid, or "
            f"filename; see `catalog --kind models`).")
    dest = model_cache_path(cache or DEFAULT_CACHE, model)
    fetch_verified(model, dest, f"model {model['name']}")
    return dest


# --------------------------------------------------------------------------- #
#  Catalog filtering + CLI (host-side)
# --------------------------------------------------------------------------- #
def catalog_query(kind: str, category: str | None = None,
                  search: str | None = None, facets: list[tuple] | None = None,
                  explicit_lib: str | None = None) -> dict:
    """Filtered catalog. Returns {'kind', 'count', 'rows', 'meta'}.

    kind='categories' lists the 19 animation categories with clip
    counts (the discovery entry point -- find the right category CODE
    by searching its English or Chinese name, then filter --kind
    animations --category CODE)."""
    facets = facets or []
    if kind == "categories":
        cats = load_categories(explicit_lib)
        rows_all = load_animations(explicit_lib)
        counts: dict[str, int] = {}
        for r in rows_all:
            counts[r["category"]] = counts.get(r["category"], 0) + 1
        rows = [{"code": c, "name": v["name"], "nameEn": v["nameEn"],
                 "clips": counts.get(c, 0)}
                for c, v in cats.items()]
        if search:
            s = search.lower()
            rows = [r for r in rows
                    if s in r["code"].lower() or s in r["name"].lower()
                    or s in r["nameEn"].lower()]
        rows.sort(key=lambda r: -r["clips"])
        meta = {"total_categories": len(cats),
                "usage": "catalog --kind animations --category <code>"}
    elif kind == "animations":
        rows = load_animations(explicit_lib)
        cats = load_categories(explicit_lib)
        if category:
            rows = [r for r in rows if r["category"].upper() == category.upper()]
        if search:
            s = search.lower()
            rows = [r for r in rows
                    if s in r["name"].lower() or s in r["nameEn"].lower()]
        for r in rows:
            r["category_name"] = cats.get(
                r["category"], {}).get("name", r["category"])
            tags = clip_tags(r["id"])
            if tags:
                r["tags"] = tags
            fr = clip_frames(r["id"])
            if fr is not None:
                r["frames"] = fr
                r["duration_s"] = round(fr / FBX_FPS, 2)
        meta = {"total_rows": 2137, "unique_after_id_dedup": 2032,
                "categories": len(cats),
                "tags_note": "elevated_root_motion = pair with set "
                             "geometry (climb/hang/leap family); "
                             "static_pose = held pose, near-zero motion"}
    elif kind == "characters":
        rows = load_characters(explicit_lib)
        valid = load_facet_options(explicit_lib)
        if facets:
            for facet, value in facets:
                if facet not in valid:
                    raise RHRefused(
                        f"unknown facet {facet!r}. Valid facets: "
                        f"{', '.join(sorted(valid))}.")
                if value not in valid[facet]:
                    raise RHRefused(
                        f"unknown value {value!r} for facet {facet!r}. "
                        f"Valid: {', '.join(valid[facet])}.")
                rows = [r for r in rows if r["facets"].get(facet) == value]
        if search:
            s = search.lower()
            rows = [r for r in rows if s in r["name"].lower()]
        meta = {"facets_applied": dict(facets)}
    elif kind == "models":
        rows = load_models(explicit_lib)
        if category:
            rows = [r for r in rows
                    if category.upper() in (r["group"], r["group_label"].upper())]
        if search:
            s = search.lower()
            rows = [r for r in rows
                    if s in r["name"].lower() or s in r["group_label"].lower()]
        meta = {"groups": sorted({r["group"] for r in rows})}
    else:
        raise RHRefused(f"--kind must be categories|animations|characters|"
                        f"models, got {kind!r}")
    return {"kind": kind, "count": len(rows), "rows": rows, "meta": meta}


def _print_catalog(res: dict, limit: int, as_json: bool) -> None:
    if as_json:
        slim = dict(res)
        slim["rows"] = res["rows"][:limit]
        print(json.dumps(slim, ensure_ascii=False, indent=1))
        return
    print(f"[rh] {res['kind']}: {res['count']} entries "
          f"(showing up to {limit})  meta={json.dumps(res['meta'], ensure_ascii=False)}")
    for r in res["rows"][:limit]:
        if res["kind"] == "categories":
            print(f"  {r['code']:<45} {r['clips']:>4}  {r['name']}  "
                  f"[{r['nameEn']}]")
        elif res["kind"] == "animations":
            tag = "" if not r.get("tags") else "  <" + ",".join(r["tags"]) + ">"
            fr = r.get("frames")
            fren = f"{fr}f/{fr/FBX_FPS:.1f}s" if fr else "-"
            print(f"  {r['id']:>6}  {r['category']:<42}  {fren:>10}  {r['name']}  "
                  f"[{r['nameEn']}]  {r['size']/1024:.0f}KB{tag}")
        elif res["kind"] == "characters":
            fcts = " ".join(f"{k}={v}" for k, v in sorted(r["facets"].items()))
            print(f"  {r['id']:>4}  {r['name']}  {fcts}")
        else:
            print(f"  {r['group']:<3}  {r['name']:<24}  {r['group_label']:<14} "
                  f"{r['size']/1048576:.2f}MB  {r['filename']}")


# --------------------------------------------------------------------------- #
#  Blender-side core (bpy imported lazily — module stays host-importable)
# --------------------------------------------------------------------------- #
def _bpy():
    try:
        import bpy  # noqa
        return bpy
    except ImportError:
        raise RHRefused(
            "this subcommand needs Blender — run it via "
            "./scripts/blrun.sh --background --python scripts/rh_canvas.py -- "
            "<subcommand> ...")


def _action_fcurves(act):
    """5.x slotted-actions compat (action.fcurves moved to
    layers[].strips[].channelbags[].fcurves)."""
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    yield from bag.fcurves
    except AttributeError:                    # 4.x
        yield from act.fcurves


def check_mixamo_rig(arm, ctx: str = "") -> dict:
    """Teacher-check an armature against the Mixamo family contract
    (65 bones, every one prefixed 'mixamorig:'). Returns a census dict;
    raises RHRefused on violation."""
    bones = list(arm.data.bones)
    n = len(bones)
    bad = [b.name for b in bones
           if not b.name.startswith(MIXAMO_PREFIX)]
    if n != MIXAMO_BONE_COUNT or bad:
        head = f"[{ctx}] " if ctx else ""
        if n != MIXAMO_BONE_COUNT:
            raise RHRefused(
                f"{head}armature '{arm.name}' has {n} bones — the RH-canvas "
                f"clip family is exactly {MIXAMO_BONE_COUNT} 'mixamorig:' "
                f"bones. This is not a Mixamo-family rig; the FBX actions "
                f"would animate nothing sensible on it.")
        raise RHRefused(
            f"{head}armature '{arm.name}' has {len(bad)} bone(s) without the "
            f"'{MIXAMO_PREFIX}' prefix (first: {bad[0]!r}) — not a "
            f"Mixamo-family rig. If you renamed bones for testing, restore "
            f"the prefix; RH-canvas clips drive 'mixamorig:' names only.")
    return {"bones": n, "prefix_ok": True}


def import_clip(clip_id: str, name: str | None = None,
                cache: str | None = None,
                explicit_lib: str | None = None) -> tuple:
    """Fetch-if-missing -> import FBX -> validated armature + report.

    NEVER transform_apply the armature (scale law / cm-fcurve law): the
    object scale (0.01,0.01,0.01) + rot X~=90deg carry the cm->m and
    Y-up->Z-up conversions; the hips fcurves stay in raw cm.
    Returns (armature_object, report_dict)."""
    bpy = _bpy()
    path = ensure_animation(clip_id, cache, explicit_lib)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)   # default settings: verified
    new = [o for o in bpy.data.objects if o not in before]
    arms = [o for o in new if o.type == 'ARMATURE']
    if not arms:
        raise RHRefused(
            f"FBX import of clip {clip_id} produced no armature — the clip "
            f"family is skeleton-only FBX; a format change upstream?")
    arm = arms[0]
    census = check_mixamo_rig(arm, "import-clip")

    sc = bpy.context.scene
    act = arm.animation_data.action if arm.animation_data else None
    if act is None:
        raise RHRefused(
            f"FBX import of clip {clip_id} produced no bound action — "
            f"unexpected for this library (every sampled clip has exactly "
            f"one take).")
    _CLIP_ACTION_REGISTRY[str(clip_id)] = (act.name, tuple(act.frame_range))
    f0, f1 = act.frame_range
    # fps-30 + frame-range laws: set BOTH, so export_frame_range=True
    # clips to the action and glTF timing is correct.
    sc.render.fps = FBX_FPS
    sc.frame_start, sc.frame_end = int(f0), int(f1)

    if name:
        arm.name = name

    import math
    mw = arm.matrix_world.copy()
    lh = mw @ arm.data.bones["mixamorig:LeftHand"].head_local
    rh = mw @ arm.data.bones["mixamorig:RightHand"].head_local
    span = (lh - rh).length                          # law 8 definition
    pts = [mw @ b.head_local for b in arm.data.bones] + \
          [mw @ b.tail_local for b in arm.data.bones]
    hips_z = None
    for fc in _action_fcurves(act):
        if fc.data_path == 'pose.bones["mixamorig:Hips"].location' \
                and fc.array_index == 2:
            vals = [kp.co[1] for kp in fc.keyframe_points]
            if vals:
                hips_z = (min(vals), max(vals))
    report = {
        "clip_id": str(clip_id),
        "file": os.path.basename(path),
        "armature": arm.name,
        "bones": census["bones"],
        "mixamorig_prefix": census["prefix_ok"],
        "obj_scale": [round(c, 5) for c in arm.scale],
        "obj_rot_x_deg": round(math.degrees(arm.rotation_euler.x), 2),
        "scale_law_note": "KEEP obj scale 0.01 + rot X~=90deg — NEVER "
                          "transform_apply (hips fcurves are raw cm)",
        "fps": sc.render.fps,
        "frame_range": [int(f0), int(f1)],
        "scene_range_set": [sc.frame_start, sc.frame_end],
        "t_pose_span_m": round(span, 4),
        "rest_bone_bbox_z_m": [round(min(p.z for p in pts), 4),
                               round(max(p.z for p in pts), 4)],
        "rest_feet_z_m": round(min(
            min((mw @ b.head_local).z, (mw @ b.tail_local).z)
            for b in arm.data.bones
            if b.name.endswith(("Foot", "Toe"))), 4),
        "hips_location_z_raw_cm": hips_z and [round(hips_z[0], 2),
                                              round(hips_z[1], 2)],
        "action": act.name,
    }
    return arm, report


def _capsule(bpy, name, p0, p1, radius, seg=14):
    """Cylinder with caps from p0 to p1 (WORLD coords) — REVIEW-RH-1b
    verified shape (bmesh create_cone, world-baked)."""
    from mathutils import Vector, Matrix
    d = Vector(p1) - Vector(p0)
    length = d.length
    if length < 1e-6:
        return None
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=radius, radius2=radius, depth=length)
    mid = (Vector(p0) + Vector(p1)) * 0.5
    rot = d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bm.transform(Matrix.Translation(mid) @ rot)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def build_mannequin(arm, name: str = "RHMannequin") -> tuple:
    """THE BODY (the platform's own dummy FBX is not archived — recon
    PART 3). Procedural capsule mesh from data.bones REST positions
    (the pose is at the clip's f1, NOT rest — build from REST).

    Order (REVIEW-RH-1b verified): build capsules -> JOIN ->
    parent_set(ARMATURE_AUTO, keep_transform=True) -> rename after join.
    Expect 65 vertex groups incl. fingers, 0 zero-weight verts;
    >4-influence verts are expected (glTF caps at 4 — law 9).
    Returns (mesh_object, report_dict)."""
    bpy = _bpy()
    check_mixamo_rig(arm, "mannequin")
    mw = arm.matrix_world.copy()
    obs = []
    for bname, rad in CAPSULE_RADII.items():
        b = arm.data.bones.get(MIXAMO_PREFIX + bname)
        if b is None:
            raise RHRefused(
                f"mannequin: bone '{MIXAMO_PREFIX}{bname}' missing from "
                f"'{arm.name}' — the capsule table expects the standard "
                f"Mixamo 65-bone set.")
        ob = _capsule(bpy, "rhseg_" + bname, mw @ b.head_local,
                      mw @ b.tail_local, rad)
        if ob:
            obs.append(ob)
    # join (A: join THEN parent — verified order)
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    mesh = bpy.context.view_layer.objects.active
    # rename AFTER join
    mesh.name = name
    mesh.data.name = name
    # rest metrics from the pre-parent world-space vertex data (capsules
    # were built at world coords; join preserves them)
    verts = mesh.data.vertices
    zs = [v.co.z for v in verts]
    rest_height = max(zs) - min(zs)
    rest_min_z = min(zs)
    # parent ARMATURE_AUTO with keep_transform (verified on 5.2.2)
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO', keep_transform=True)
    # census
    zero_w = 0
    over4 = 0
    for v in mesh.data.vertices:
        tot = sum(g.weight for g in v.groups)
        if tot < 1e-6:
            zero_w += 1
        if len(v.groups) > 4:
            over4 += 1
    report = {
        "mesh": mesh.name,
        "armature": arm.name,
        "segments": len(obs),
        "verts": len(mesh.data.vertices),
        "vertex_groups": len(mesh.vertex_groups),
        "zero_weight_verts": zero_w,
        "over_4_influence_verts": over4,
        "over4_note": ">4 influences are expected; the glTF exporter caps "
                      "at 4 (cosmetic — law 9)",
        "rest_height_m": round(rest_height, 4),
        "rest_min_z_m": round(rest_min_z, 4),
        "placement_law": "armature placed first; never move this mesh "
                         "after binding (bind breaks)",
    }
    return mesh, report


def _resolve_armature_arg(target):
    """--armature accepts an armature name, a MESH name/object (auto-
    resolves mesh.parent or the ARMATURE modifier's object), or an
    armature object directly. NEVER returns the mesh itself — assigning
    an action to a mesh's animation_data is a silent no-op (the review's
    P3 finding)."""
    bpy = _bpy()
    if isinstance(target, str):
        obj = bpy.data.objects.get(target)
        if obj is None:
            raise RHRefused(
                f"no object named {target!r} in the scene. --armature "
                f"takes an armature name or a mesh name (the mesh's "
                f"parent armature is auto-resolved).")
        target = obj
    if target.type == 'ARMATURE':
        return target
    if target.type == 'MESH':
        arm = target.parent if target.parent and target.parent.type == 'ARMATURE' else None
        if arm is None:
            for m in target.modifiers:
                if m.type == 'ARMATURE' and m.object:
                    arm = m.object
                    break
        if arm is None:
            raise RHRefused(
                f"mesh '{target.name}' has no armature parent or ARMATURE "
                f"modifier — nothing to bind to. (bind assigns to the "
                f"ARMATURE's animation_data; assigning to a mesh is a "
                f"silent no-op.)")
        return arm
    raise RHRefused(
        f"object '{target.name}' is a {target.type}, not an armature or a "
        f"skinned mesh.")


# session-level registry: clip id -> (action name, frame_range
# fingerprint), so a bind-by-id inside one scene process reuses the
# action from import-clip instead of importing a duplicate (keeps
# bpy.data.actions to one-per-clip — the export one-object-one-action
# law, AGENTS.md #104/#105).
#
# THE FINGERPRINT LAW (s39 decoy probe): every Mixamo FBX action lands
# under the SAME name ('Armature|mixamo.com|Layer0' — Blender suffixes
# .001/.002 only within one bpy.data lifetime). After a scene reset
# (read_factory_settings) a bare name lookup returns a DIFFERENT clip's
# action — the registry silently mis-binds. The frame_range fingerprint
# validates the hit; a mismatch is treated as a miss (fresh import).
_CLIP_ACTION_REGISTRY: dict[str, tuple[str, tuple[float, float]]] = {}


def _resolve_clip_action(clip, cache=None, explicit_lib=None):
    """--clip accepts an animation catalog id (fetch+import, keep only
    the action), an armature name (its bound action), or an action name."""
    bpy = _bpy()
    if isinstance(clip, str):
        # 0) already imported this clip in this session -> reuse (ONLY
        #    when the frame-range fingerprint matches — see the law above)
        reg = _CLIP_ACTION_REGISTRY.get(str(clip))
        if reg:
            act = bpy.data.actions.get(reg[0])
            if act is not None and \
                    tuple(int(v) for v in act.frame_range) == \
                    tuple(int(v) for v in reg[1]):
                return act, None
            # stale entry (scene reset / name collision) -> fall through
            # to a fresh import and re-register below
        # 1) catalog id -> import fresh (idempotent), extract the action
        try:
            anim = _find_animation(clip, explicit_lib)
        except RHRefused:
            anim = None                       # library present check failed
        if anim is not None:
            src_arm, _rep = import_clip(clip, cache=cache,
                                        explicit_lib=explicit_lib)
            act = src_arm.animation_data.action
            # caller assigns act to the target first, so keep a reference;
            # remove the source armature object (skeleton-only clutter)
            return act, src_arm
        # 2) armature object with a bound action
        obj = bpy.data.objects.get(clip)
        if obj is not None and obj.type == 'ARMATURE':
            act = obj.animation_data.action if obj.animation_data else None
            if act is None:
                raise RHRefused(
                    f"armature '{clip}' has no bound action to bind from.")
            return act, None
        # 3) action by name
        act = bpy.data.actions.get(clip)
        if act is not None:
            return act, None
        raise RHRefused(
            f"--clip {clip!r} matches no animation id, armature name, or "
            f"action name. Use a catalog id (see `catalog --kind "
            f"animations`).")
    # an Action object passed programmatically
    return clip, None


def bind(target, clip, cache: str | None = None,
         explicit_lib: str | None = None) -> dict:
    """Assign a clip's action to an armature.

    The MESH-arg auto-resolution law: `target` may be the skinned mesh —
    its parent armature (or ARMATURE modifier object) is resolved and the
    ACTION goes on the ARMATURE's animation_data (assigning to the mesh
    is Blender's silent no-op class — review P3).
    Sets scene range from act.frame_range + fps=30 (laws 3-4).
    Teacher-refuses non-Mixamo / wrong-bone-count targets.

    CHANNEL-MATCH VALIDATION (s39-U2 P1): a rig can pass the
    count+prefix gate with WRONG bone names (e.g. one renamed bone) —
    the assignment 'succeeds' but those fcurves drive nothing (0.0 m
    motion, frozen joints: the silent-failure class). After assigning,
    every fcurve's data_path must resolve to a real pose bone on the
    target: matched == 0 -> REFUSED; 0 < matched < total -> bound, but
    the rep carries orphaned_channels (rename those bones back or
    retarget)."""
    bpy = _bpy()
    arm = _resolve_armature_arg(target)
    check_mixamo_rig(arm, "bind")
    act, src_arm = _resolve_clip_action(clip, cache, explicit_lib)
    # a hand-named action must target mixamorig pose bones
    n_mix = 0
    for fc in _action_fcurves(act):
        if fc.data_path.startswith('pose.bones["mixamorig:'):
            n_mix += 1
    if n_mix == 0:
        raise RHRefused(
            f"action '{act.name}' has no 'mixamorig:' pose fcurves — it is "
            f"not an RH-canvas clip action; refusing to bind it to "
            f"'{arm.name}'.")
    # channel-match: every fcurve's bone must exist on the target
    pose_names = set(p.name for p in arm.pose.bones)
    matched = 0
    total = 0
    import re as _re
    _bone_re = _re.compile(r'pose\.bones\["([^"]+)"\]')
    for fc in _action_fcurves(act):
        m = _bone_re.match(fc.data_path)
        if not m:
            continue
        total += 1
        if m.group(1) in pose_names:
            matched += 1
    if total and matched == 0:
        raise RHRefused(
            f"action '{act.name}' has {total} pose-bone fcurve channels "
            f"but NONE of them name a bone on armature '{arm.name}' "
            f"(0/{total} matched). The rig passed the 65-bone "
            f"'mixamorig:' census but its bone NAMES do not match the "
            f"clip family — binding would animate nothing (the silent "
            f"zero-motion trap). Restore the standard Mixamo bone names "
            f"or retarget the action.")
    orphaned = total - matched
    # action hygiene (s39-U2 P2): the FBX importer pins every imported
    # action with fake_user; when we swap an armature to a NEW clip the
    # replaced action must drop its pin or it ships in glTF ACTIONS
    # exports forever (the AGENTS.md #104/#105 'air dance' class).
    old = arm.animation_data.action if arm.animation_data else None
    if old is not None and old != act:
        old.use_fake_user = False
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act           # slot auto-assigns on 5.2.2
    if arm.animation_data.action_slot is None and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    sc = bpy.context.scene
    f0, f1 = act.frame_range
    sc.render.fps = FBX_FPS
    sc.frame_start, sc.frame_end = int(f0), int(f1)
    if src_arm is not None and src_arm != arm:
        bpy.data.objects.remove(src_arm, do_unlink=True)
    rep = {
        "armature": arm.name,
        "action": act.name,
        "slot_assigned": arm.animation_data.action_slot is not None,
        "channels_matched": f"{matched}/{total}",
        "orphaned_channels": orphaned,
        "fps": sc.render.fps,
        "scene_range": [sc.frame_start, sc.frame_end],
        "action_frame_range": [int(f0), int(f1)],
        "note": "action assigned to the ARMATURE (mesh args were "
                "auto-resolved); moving the mesh now would break the bind",
    }
    if orphaned:
        rep["warning"] = (f"{orphaned} fcurve channel(s) name bones that "
                          f"do not exist on '{arm.name}' — those joints "
                          f"will NOT animate (renamed bones? restore the "
                          f"'mixamorig:' names or retarget).")
    return rep


def purge_unassigned() -> dict:
    """Hygiene helper (s39-U2): remove actions that are pinned
    (fake_user, set by the FBX importer on every clip import) but not
    assigned to ANY object — the class that otherwise ships in glTF
    ACTIONS exports ('air dance'). Returns {'removed': [names]}."""
    bpy = _bpy()
    assigned = set()
    for o in bpy.data.objects:
        if o.animation_data and o.animation_data.action:
            assigned.add(o.animation_data.action.name)
    removed = []
    for ac in list(bpy.data.actions):
        if ac.name not in assigned and ac.use_fake_user:
            removed.append(ac.name)
            bpy.data.actions.remove(ac)
    return {"removed": removed}


def import_statue(model_name: str, ground_snap: bool = False,
                  cache: str | None = None,
                  explicit_lib: str | None = None) -> tuple:
    """Import a director GLTF statue (static, unrigged — recon PART 2:
    meters, Z-up, feet at z~=0 verified; do NOT expect to animate it).

    --ground-snap offsets each top-level root object's z so its subtree's
    lowest vertex sits at exactly 0 (statues ship at |min_z| < 10 mm; the
    snap is a no-op-class correction — the ARMATURE-like root object is
    moved, never the child meshes).
    Returns (imported_objects, report_dict)."""
    bpy = _bpy()
    path = ensure_model(model_name, cache, explicit_lib)
    model = _find_model(model_name, explicit_lib)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)  # default import: verified
    new = [o for o in bpy.data.objects if o not in before]
    if not new:
        raise RHRefused(
            f"GLTF import of model {model_name!r} produced no objects — "
            f"unexpected (all 99 sampled import clean).")
    meshes = [o for o in new if o.type == 'MESH']
    polys = sum(len(o.data.polygons) for o in meshes)

    def _subtree_min_z(root):
        zs = []
        stack, seen = [root], set()
        while stack:
            o = stack.pop()
            if o.name in seen:
                continue
            seen.add(o.name)
            if o.type == 'MESH':
                mw = o.matrix_world
                zs.extend((mw @ v.co).z for v in o.data.vertices)
            stack.extend(o.children)
        return min(zs) if zs else None

    roots = [o for o in new if o.parent is None or o.parent not in new]
    min_z = min((z for z in (_subtree_min_z(r) for r in roots)
                 if z is not None), default=None)
    height = None
    all_zs = []
    for o in meshes:
        mw = o.matrix_world
        all_zs.extend((mw @ v.co).z for v in o.data.vertices)
    if all_zs:
        height = max(all_zs) - min(all_zs)
        min_z = min(min_z, min(all_zs))
    snap_delta = None
    if ground_snap and min_z is not None and abs(min_z) > 1e-9:
        from mathutils import Matrix
        for r in roots:
            rz = _subtree_min_z(r)
            if rz is None:
                continue
            r.matrix_world = Matrix.Translation((0.0, 0.0, -rz)) @ r.matrix_world
        snap_delta = -min_z
        bpy.context.view_layer.update()
        # re-measure
        all_zs = []
        for o in meshes:
            mw = o.matrix_world
            all_zs.extend((mw @ v.co).z for v in o.data.vertices)
        min_z = min(all_zs) if all_zs else None
        height = (max(all_zs) - min(all_zs)) if all_zs else None
    report = {
        "model": model["name"] if model else str(model_name),
        "group": model["group"] if model else None,
        "file": os.path.basename(path),
        "objects": [o.name for o in new],
        "meshes": len(meshes),
        "polys": polys,
        "height_m": round(height, 4) if height is not None else None,
        "feet_min_z_m": round(min_z, 4) if min_z is not None else None,
        "ground_snap": bool(ground_snap),
        "snap_delta_m": round(snap_delta, 4) if snap_delta is not None else None,
        "grounding": ("PASS (|min_z| < 10 mm band)" if min_z is not None
                      and abs(min_z) < 0.010 else
                      "OUT OF BAND (|min_z| >= 10 mm) — use --ground-snap"),
        "note": "static statue: 0 bones/skins/anims (cannot animate); "
                "meters/Z-up verified",
    }
    return new, report


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def _argv() -> list[str]:
    """Args after '--' when run via blrun.sh, else sys.argv[1:]."""
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return sys.argv[1:]


def _hoist_common(argv: list[str]) -> tuple:
    """argparse subparsers cannot see main-level flags, so --library /
    --cache are accepted BEFORE or AFTER the subcommand: pull them out of
    argv here, apply after parse. Returns (clean_argv, library, cache)."""
    lib = cache = None
    out = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--library" and i + 1 < len(argv):
            lib = argv[i + 1]
            i += 2
            continue
        if a == "--cache" and i + 1 < len(argv):
            cache = argv[i + 1]
            i += 2
            continue
        if a.startswith("--library="):
            lib = a.split("=", 1)[1]
            i += 1
            continue
        if a.startswith("--cache="):
            cache = a.split("=", 1)[1]
            i += 1
            continue
        out.append(a)
        i += 1
    return out, lib, cache


def _json_print(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def main(argv=None) -> int:
    argv = argv if argv is not None else _argv()
    argv, hoisted_lib, hoisted_cache = _hoist_common(argv)
    ap = argparse.ArgumentParser(
        prog="rh_canvas.py",
        description="RH-canvas mocap clips + director statues "
                    "(catalog/fetch host-side; import/mannequin/bind Blender-side)")
    ap.add_argument("--library", default=None,
                    help="path to an RH-canvas clone, their common parent, "
                         "or any sibling dir (else env RH_CANVAS_LIB; "
                         "auto-discovers RH-canvas-animations / "
                         "RH-canvas-characters by dir name)")
    ap.add_argument("--cache", default=None,
                    help=f"cache dir (default env RH_CANVAS_CACHE else "
                         f"{DEFAULT_CACHE})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("catalog", help="browse catalogs (no network)")
    p.add_argument("--kind", default="animations",
                   choices=["categories", "animations", "characters",
                            "models"])
    p.add_argument("--category", default=None,
                   help="animations: category CODE (list them: --kind "
                        "categories); models: group JC/RW/DJ/CJ/JT")
    p.add_argument("--search", default=None,
                   help="substring on name (Chinese) / nameEn (search-hint only)")
    p.add_argument("--facet", action="append", default=[], metavar="FACET=VALUE",
                   help="characters 9-facet taxonomy filter (repeatable), "
                        "e.g. --facet gender=female --facet species=elf")
    p.add_argument("--json", action="store_true")
    p.add_argument("--limit", type=int, default=40)

    p = sub.add_parser("fetch", help="sha256-verified CDN download (idempotent)")
    p.add_argument("--ids", required=True,
                   help="comma-separated animation ids and/or model names "
                        "(e.g. 2846,2825,Farmer)")

    p = sub.add_parser("import-clip", help="FBX clip -> armature + action")
    p.add_argument("--id", required=True, help="animation catalog id (STRING)")
    p.add_argument("--name", default=None, help="rename the armature")

    p = sub.add_parser("mannequin", help="capsule body skinned to the Mixamo rig")
    p.add_argument("--name", default="RHMannequin")
    p.add_argument("--armature", default=None,
                   help="armature name (default: the scene's single "
                        "Mixamo armature)")

    p = sub.add_parser("bind", help="assign a clip action to an armature")
    p.add_argument("--clip", required=True,
                   help="animation id | armature name | action name")
    p.add_argument("--armature", required=True,
                   help="armature name or MESH name (auto-resolves to "
                        "mesh.parent / ARMATURE modifier object)")

    p = sub.add_parser("import-statue", help="static director GLTF statue")
    p.add_argument("--model", required=True, help="model name (e.g. Farmer)")
    p.add_argument("--ground-snap", action="store_true",
                   help="offset root-object z so feet sit at exactly 0")

    args = ap.parse_args(argv)
    # hoisted common flags win over the parse defaults (they may have
    # appeared before OR after the subcommand)
    args.library = hoisted_lib or args.library
    args.cache = hoisted_cache or args.cache
    try:
        if args.cmd == "catalog":
            facets = []
            for f in args.facet:
                if "=" not in f:
                    raise RHRefused(
                        f"--facet expects FACET=VALUE, got {f!r} (e.g. "
                        f"--facet gender=female)")
                k, v = f.split("=", 1)
                facets.append((k.strip(), v.strip()))
            res = catalog_query(args.kind, args.category, args.search,
                                facets, args.library)
            _print_catalog(res, args.limit, args.json)
        elif args.cmd == "fetch":
            ids = [i.strip() for i in args.ids.split(",") if i.strip()]
            for r in fetch_ids(ids, args.cache, args.library):
                print(f"[rh] fetch {r['kind']} {r['id']} ({r['name']}): "
                      f"{r['status']} -> {r['dest']}")
        elif args.cmd == "import-clip":
            _arm, rep = import_clip(args.id, args.name, args.cache,
                                    args.library)
            _json_print(rep)
        elif args.cmd == "mannequin":
            bpy = _bpy()
            if args.armature:
                arm = _resolve_armature_arg(args.armature)
            else:
                arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
                if len(arms) != 1:
                    raise RHRefused(
                        f"scene has {len(arms)} armatures — pass --armature "
                        f"(candidates: {', '.join(o.name for o in arms) or 'none'})")
                arm = arms[0]
            _mesh, rep = build_mannequin(arm, args.name)
            _json_print(rep)
        elif args.cmd == "bind":
            rep = bind(args.armature, args.clip, args.cache, args.library)
            _json_print(rep)
        elif args.cmd == "import-statue":
            _objs, rep = import_statue(args.model, args.ground_snap,
                                       args.cache, args.library)
            _json_print(rep)
        else:                                   # pragma: no cover
            ap.error(f"unknown subcommand {args.cmd!r}")
    except RHRefused as e:
        print(f"[rh] REFUSED: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
