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
      throw ArgumentError.value(waypoints.length, 'waypoints', '최대 10개');
    }
    if (!Platform.isAndroid) {
      throw const NavigationNotConfiguredException();
    }
    try {
      await _channel.invokeMethod<bool>('startGuidance', {
        'name': destination.name ?? '코스 시작점',
        'latitude': destination.latitude,
        'longitude': destination.longitude,
      });
    } on PlatformException catch (error) {
      throw StateError(error.message ?? 'TMAP 길안내를 실행하지 못했습니다.');
    }
  }
}
