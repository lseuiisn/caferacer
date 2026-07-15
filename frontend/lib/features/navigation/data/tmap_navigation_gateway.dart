import 'dart:io';

import 'package:flutter/services.dart';

import '../domain/navigation_gateway.dart';

class TmapNavigationGateway implements NavigationGateway {
  static const _channel = MethodChannel('waypoint/tmap_navigation');

  @override
  Future<void> startGuidance({
    required NavigationPoint origin,
    required NavigationPoint destination,
    List<NavigationPoint> waypoints = const [],
  }) async {
    if (waypoints.length > 10) {
      throw ArgumentError.value(waypoints.length, 'waypoints', 'Maximum is 10');
    }
    if (!Platform.isAndroid) {
      throw const NavigationNotConfiguredException();
    }
    try {
      await _channel.invokeMethod<bool>('startGuidance', {
        'origin': _encodePoint(origin),
        'destination': _encodePoint(destination),
        'waypoints': waypoints.map(_encodePoint).toList(growable: false),
      });
    } on PlatformException catch (error) {
      throw StateError(error.message ?? 'Could not start TMAP guidance.');
    }
  }

  Map<String, Object?> _encodePoint(NavigationPoint point) => {
    'name': point.name,
    'latitude': point.latitude,
    'longitude': point.longitude,
  };
}
