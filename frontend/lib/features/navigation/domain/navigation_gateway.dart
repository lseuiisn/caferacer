class NavigationPoint {
  const NavigationPoint({
    required this.latitude,
    required this.longitude,
    this.name,
  });

  final double latitude;
  final double longitude;
  final String? name;
}

abstract interface class NavigationGateway {
  Future<void> startGuidance({
    required NavigationPoint origin,
    required NavigationPoint destination,
    List<NavigationPoint> waypoints = const [],
  });
}

class NavigationNotConfiguredException implements Exception {
  const NavigationNotConfiguredException();

  @override
  String toString() =>
      'TMAP 앱 길안내를 실행할 수 없습니다. TMAP 설치와 API 키를 확인해 주세요.';
}
