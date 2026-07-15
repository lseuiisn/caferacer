package com.example.frontend

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PointF
import android.util.Log
import android.view.View
import com.skt.Tmap.TMapMarkerItem
import com.skt.Tmap.TMapPoint
import com.skt.Tmap.TMapPolyLine
import com.skt.Tmap.TMapView
import com.skt.Tmap.poi_item.TMapPOIItem
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
    private val mapView = TMapView(context)

    init {
        val apiKey = BuildConfig.TMAP_MAP_API_KEY
        check(apiKey.isNotBlank()) {
            "TMAP_MAP_API_KEY is missing. Add it to android/local.properties."
        }
        mapView.setHttpsMode(true)
        mapView.setSKTMapApiKey(apiKey)
        configureCenter(args["center"] as? Map<*, *>, args["zoom"] as? Number)
        configurePolyline(args["polylines"] as? List<*>)
        configureMarkers(args["markers"] as? List<*>)
        mapView.setClick()
        mapView.setOnClickListenerCallBack(object : TMapView.OnClickListenerCallback {
            override fun onPressEvent(
                markers: ArrayList<TMapMarkerItem>,
                poiItems: ArrayList<TMapPOIItem>,
                point: TMapPoint,
                screenPoint: PointF,
            ): Boolean {
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
                return true
            }

            override fun onPressUpEvent(
                markers: ArrayList<TMapMarkerItem>,
                poiItems: ArrayList<TMapPOIItem>,
                point: TMapPoint,
                screenPoint: PointF,
            ): Boolean = true
        })
    }

    private fun configureCenter(center: Map<*, *>?, zoom: Number?) {
        val latitude = (center?.get("latitude") as? Number)?.toDouble() ?: return
        val longitude = (center["longitude"] as? Number)?.toDouble() ?: return
        mapView.setCenterPoint(longitude, latitude)
        mapView.setZoomLevel(zoom?.toInt() ?: 12)
    }

    private fun configureMarkers(markers: List<*>?) {
        markers.orEmpty().forEach { raw ->
            val marker = raw as? Map<*, *> ?: return@forEach
            val latitude = (marker["latitude"] as? Number)?.toDouble() ?: return@forEach
            val longitude = (marker["longitude"] as? Number)?.toDouble() ?: return@forEach
            val id = marker["id"]?.toString() ?: return@forEach
            val item = TMapMarkerItem().apply {
                setID(id)
                setTMapPoint(TMapPoint(latitude, longitude))
                setName(marker["title"]?.toString() ?: "")
                setCalloutTitle(marker["title"]?.toString() ?: "")
                setCalloutSubTitle(marker["subtitle"]?.toString() ?: "")
                setCanShowCallout(true)
                setIcon(markerBitmap(marker["color"]?.toString()))
            }
            mapView.addMarkerItem(id, item)
        }
    }

    private fun configurePolyline(polylines: List<*>?) {
        polylines.orEmpty().forEachIndexed { index, raw ->
            val lineData = raw as? Map<*, *> ?: return@forEachIndexed
            val points = lineData["points"] as? List<*> ?: return@forEachIndexed
            val polyline = TMapPolyLine().apply {
                setLineColor(Color.rgb(38, 99, 235))
                setLineWidth(8f)
            }
            points.forEach { point ->
                val pair = point as? List<*> ?: return@forEach
                val latitude = (pair.getOrNull(0) as? Number)?.toDouble() ?: return@forEach
                val longitude = (pair.getOrNull(1) as? Number)?.toDouble() ?: return@forEach
                polyline.addLinePoint(TMapPoint(latitude, longitude))
            }
            mapView.addTMapPolyLine("course_$index", polyline)
        }
    }

    private fun markerBitmap(type: String?): Bitmap {
        val color = when (type) {
            "start" -> Color.rgb(22, 163, 74)
            "destination" -> Color.rgb(220, 38, 38)
            "waypoint" -> Color.rgb(234, 88, 12)
            "cafe" -> Color.rgb(120, 53, 15)
            else -> Color.rgb(37, 99, 235)
        }
        return Bitmap.createBitmap(48, 48, Bitmap.Config.ARGB_8888).also { bitmap ->
            Canvas(bitmap).drawCircle(24f, 24f, 16f, Paint(Paint.ANTI_ALIAS_FLAG).apply {
                this.color = color
                style = Paint.Style.FILL
            })
        }
    }

    override fun getView(): View = mapView

    override fun dispose() {
        runCatching { mapView.destroy() }
            .onFailure { Log.w("WayPoint", "TMAP view disposal failed", it) }
    }
}
