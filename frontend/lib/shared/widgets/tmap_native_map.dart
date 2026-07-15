import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class TmapNativeMarker {
  const TmapNativeMarker({
    required this.id,
    required this.latitude,
    required this.longitude,
    required this.title,
    this.subtitle = '',
    this.color = 'default',
  });

  final String id;
  final double latitude;
  final double longitude;
  final String title;
  final String subtitle;
  final String color;

  Map<String, Object> toJson() => {
    'id': id,
    'latitude': latitude,
    'longitude': longitude,
    'title': title,
    'subtitle': subtitle,
    'color': color,
  };
}

class TmapNativeMap extends StatefulWidget {
  const TmapNativeMap({
    required this.centerLatitude,
    required this.centerLongitude,
    required this.markers,
    this.polylines = const [],
    this.zoom = 12,
    this.onMarkerTap,
    this.onMapTap,
    super.key,
  });

  final double centerLatitude;
  final double centerLongitude;
  final List<TmapNativeMarker> markers;
  final List<List<List<double>>> polylines;
  final int zoom;
  final ValueChanged<String>? onMarkerTap;
  final void Function(double latitude, double longitude)? onMapTap;

  @override
  State<TmapNativeMap> createState() => _TmapNativeMapState();
}

class _TmapNativeMapState extends State<TmapNativeMap> {
  late final String _channelName =
      'waypoint/tmap_map/${DateTime.now().microsecondsSinceEpoch}-${Random().nextInt(1 << 32)}';
  late final MethodChannel _channel = MethodChannel(_channelName);

  @override
  void initState() {
    super.initState();
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'markerTapped') {
        final args = call.arguments as Map<dynamic, dynamic>;
        widget.onMarkerTap?.call(args['id'] as String);
      } else if (call.method == 'mapTapped') {
        final args = call.arguments as Map<dynamic, dynamic>;
        widget.onMapTap?.call(
          (args['latitude'] as num).toDouble(),
          (args['longitude'] as num).toDouble(),
        );
      }
    });
  }

  @override
  void dispose() {
    _channel.setMethodCallHandler(null);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AndroidView(
    viewType: 'waypoint/tmap_map',
    layoutDirection: TextDirection.ltr,
    creationParams: {
      'channel': _channelName,
      'center': {
        'latitude': widget.centerLatitude,
        'longitude': widget.centerLongitude,
      },
      'zoom': widget.zoom,
      'markers': widget.markers.map((marker) => marker.toJson()).toList(),
      'polylines': widget.polylines
          .map((points) => {'points': points})
          .toList(),
    },
    creationParamsCodec: const StandardMessageCodec(),
  );
}
