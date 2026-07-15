package com.example.frontend

import com.skt.Tmap.TMapTapi
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
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
            val name = call.argument<String>("name") ?: "코스 시작점"
            val latitude = call.argument<Double>("latitude")
            val longitude = call.argument<Double>("longitude")
            if (latitude == null || longitude == null) {
                result.error("INVALID_COORDINATE", "목적지 좌표가 필요합니다.", null)
                return@setMethodCallHandler
            }
            runCatching {
                val tapi = TMapTapi(this).apply {
                    setSKTMapAuthentication(BuildConfig.TMAP_MAP_API_KEY)
                }
                if (!tapi.isTmapApplicationInstalled) {
                    error("TMAP 앱이 설치되어 있지 않습니다.")
                }
                check(tapi.invokeNavigate(name, longitude.toFloat(), latitude.toFloat(), 0, true)) {
                    "TMAP 길안내를 실행하지 못했습니다."
                }
            }.onSuccess {
                result.success(true)
            }.onFailure { error ->
                result.error("TMAP_LAUNCH_FAILED", error.message, null)
            }
        }
    }
}
