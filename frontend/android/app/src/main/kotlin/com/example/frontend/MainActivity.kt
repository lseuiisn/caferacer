package com.example.frontend

import com.skt.tmap.TMapTapi
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        flutterEngine.platformViewsController.registry.registerViewFactory(
            "waypoint/tmap_map",
            TmapMapViewFactory(flutterEngine.dartExecutor.binaryMessenger),
        )
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "waypoint/tmap_navigation",
        ).setMethodCallHandler { call, result ->
            if (call.method != "startGuidance") {
                result.notImplemented()
                return@setMethodCallHandler
            }

            runCatching { startTmapGuidance(call) }
                .onSuccess { result.success(true) }
                .onFailure { error ->
                    result.error("TMAP_LAUNCH_FAILED", error.message, null)
                }
        }
    }

    private fun startTmapGuidance(call: MethodCall) {
        val destination = call.argument<Map<*, *>>("destination")
        val origin = call.argument<Map<*, *>>("origin")
        val waypoints = call.argument<List<Map<*, *>>>("waypoints").orEmpty().take(10)

        val destinationName = destination?.get("name")?.toString()
            ?: call.argument<String>("name")
            ?: "Course start"
        val destinationLatitude = coordinate(destination, "latitude")
            ?: call.argument<Double>("latitude")
            ?: error("Destination latitude is required.")
        val destinationLongitude = coordinate(destination, "longitude")
            ?: call.argument<Double>("longitude")
            ?: error("Destination longitude is required.")

        val tapi = TMapTapi(this).apply {
            setSKTmapAuthentication(BuildConfig.TMAP_MAP_API_KEY)
        }
        check(tapi.isTmapApplicationInstalled()) {
            "TMAP is not installed."
        }

        val routeInfo = hashMapOf(
            "rGoName" to destinationName,
            "rGoX" to destinationLongitude.toString(),
            "rGoY" to destinationLatitude.toString(),
            "rSOpt" to "0",
        )
        addRoutePoint(routeInfo, "rSt", origin, "Current location")
        waypoints.forEachIndexed { index, point ->
            addRoutePoint(routeInfo, "rV${index + 1}", point, "Waypoint ${index + 1}")
        }

        check(tapi.invokeRoute(routeInfo)) {
            "Could not start TMAP guidance."
        }
    }

    private fun addRoutePoint(
        routeInfo: HashMap<String, String>,
        prefix: String,
        point: Map<*, *>?,
        fallbackName: String,
    ) {
        val latitude = coordinate(point, "latitude") ?: return
        val longitude = coordinate(point, "longitude") ?: return
        routeInfo["${prefix}Name"] = point?.get("name")?.toString() ?: fallbackName
        routeInfo["${prefix}X"] = longitude.toString()
        routeInfo["${prefix}Y"] = latitude.toString()
    }

    private fun coordinate(point: Map<*, *>?, key: String): Double? =
        (point?.get(key) as? Number)?.toDouble()
}
