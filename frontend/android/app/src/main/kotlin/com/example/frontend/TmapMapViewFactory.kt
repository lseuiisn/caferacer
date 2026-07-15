package com.example.frontend

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PointF
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import com.skt.tmap.TMapPoint
import com.skt.tmap.TMapView
import com.skt.tmap.overlay.TMapMarkerItem
import com.skt.tmap.overlay.TMapPolyLine
import com.skt.tmap.poi.TMapPOIItem
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.StandardMessageCodec
import io.flutter.plugin.platform.PlatformView
import io.flutter.plugin.platform.PlatformViewFactory

class TmapMapViewFactory(
    private val messenger: BinaryMessenger,
) : PlatformViewFactory(StandardMessageCodec.INSTANCE) {
    override fun create(context: Context, viewId: Int, args: Any?): PlatformView {
        @Suppress("UNCHECKED_CAST")
        return TmapMapPlatformView(context, args as? Map<String, Any?> ?: emptyMap(), messenger)
    }
}

private class TmapMapPlatformView(
    context: Context,
    args: Map<String, Any?>,
    messenger: BinaryMessenger,
) : PlatformView {
    private val channel = MethodChannel(
        messenger,
        args["channel"] as? String ?: "waypoint/tmap_map",
    )
    private val rootView = LayoutInflater.from(context)
        .inflate(R.layout.tmap_platform_view, null, false)
    private val mapView = rootView.findViewById<TMapView>(R.id.tmap_view)

    init {
        val apiKey = BuildConfig.TMAP_MAP_API_KEY
        check(apiKey.isNotBlank()) {
            "TMAP_MAP_API_KEY is missing. Add it to android/local.properties."
        }
        mapView.setSKTMapApiKey(apiKey)
        mapView.setOnMapReadyListener(object : TMapView.OnMapReadyListener {
            override fun onMapReady() {
                configureCenter(args["center"] as? Map<*, *>, args["zoom"] as? Number)
                configurePolyline(args["polylines"] as? List<*>)
                configureMarkers(args["markers"] as? List<*>)
            }
        })
        mapView.setOnClickListenerCallback(object : TMapView.OnClickListenerCallback {
            override fun onPressDown(
                markers: ArrayList<TMapMarkerItem>,
                poiItems: ArrayList<TMapPOIItem>,
                point: TMapPoint,
                screenPoint: PointF,
            ) {
                val marker = markers.firstOrNull()
                marker?.id?.let { id ->
                    channel.invokeMethod("markerTapped", mapOf("id" to id))
                }
                if (marker == null) {
                    channel.invokeMethod(
                        "mapTapped",
                        mapOf("latitude" to point.latitude, "longitude" to point.longitude),
                    )
                }
            }

            override fun onPressUp(
                markers: ArrayList<TMapMarkerItem>,
                poiItems: ArrayList<TMapPOIItem>,
                point: TMapPoint,
                screenPoint: PointF,
            ) = Unit
        })
        mapView.onResume()
    }

    private fun configureCenter(center: Map<*, *>?, zoom: Number?) {
        val latitude = (center?.get("latitude") as? Number)?.toDouble() ?: return
        val longitude = (center["longitude"] as? Number)?.toDouble() ?: return
        mapView.setCenterPoint(latitude, longitude)
        mapView.setZoomLevel(zoom?.toInt() ?: 12)
    }

    private fun configureMarkers(markers: List<*>?) {
        markers.orEmpty().forEach { raw ->
            val marker = raw as? Map<*, *> ?: return@forEach
            val latitude = (marker["latitude"] as? Number)?.toDouble() ?: return@forEach
            val longitude = (marker["longitude"] as? Number)?.toDouble() ?: return@forEach
            val id = marker["id"]?.toString() ?: return@forEach
            val item = TMapMarkerItem().apply {
                setId(id)
                setTMapPoint(TMapPoint(latitude, longitude))
                setName(marker["title"]?.toString() ?: "")
                setCalloutTitle(marker["title"]?.toString() ?: "")
                setCalloutSubTitle(marker["subtitle"]?.toString() ?: "")
                setCanShowCallout(true)
                setIcon(markerBitmap(marker["color"]?.toString()))
            }
            mapView.addTMapMarkerItem(item)
        }
    }

    private fun configurePolyline(polylines: List<*>?) {
        polylines.orEmpty().forEachIndexed { index, raw ->
            val lineData = raw as? Map<*, *> ?: return@forEachIndexed
            val points = lineData["points"] as? List<*> ?: return@forEachIndexed
            val polyline = TMapPolyLine().apply {
                setID(lineData["id"]?.toString() ?: "course_$index")
                setLineColor(
                    runCatching {
                        Color.parseColor(lineData["color"]?.toString() ?: "#111111")
                    }.getOrDefault(Color.BLACK),
                )
                setLineAlpha(255)
                setLineWidth((lineData["width"] as? Number)?.toFloat() ?: 8f)
            }
            points.forEach { point ->
                val pair = point as? List<*> ?: return@forEach
                val latitude = (pair.getOrNull(0) as? Number)?.toDouble() ?: return@forEach
                val longitude = (pair.getOrNull(1) as? Number)?.toDouble() ?: return@forEach
                polyline.addLinePoint(TMapPoint(latitude, longitude))
            }
            mapView.addTMapPolyLine(polyline)
        }
    }

    private fun markerBitmap(type: String?): Bitmap {
        val color = when (type) {
            "start" -> Color.rgb(200, 255, 0)
            "destination" -> Color.rgb(17, 17, 17)
            "waypoint" -> Color.rgb(255, 122, 0)
            "cafe" -> Color.rgb(17, 17, 17)
            else -> Color.rgb(50, 116, 246)
        }
        return Bitmap.createBitmap(48, 48, Bitmap.Config.ARGB_8888).also { bitmap ->
            Canvas(bitmap).drawCircle(24f, 24f, 16f, Paint(Paint.ANTI_ALIAS_FLAG).apply {
                this.color = color
                style = Paint.Style.FILL
            })
        }
    }

    override fun getView(): View = rootView

    override fun dispose() {
        runCatching {
            mapView.onPause()
            mapView.onDestroy()
        }
            .onFailure { Log.w("WayPoint", "TMAP view disposal failed", it) }
    }
}
