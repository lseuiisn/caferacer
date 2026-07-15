import 'dart:async';
import 'dart:io';

import 'package:geolocator/geolocator.dart';

import '../../../core/network/api_client.dart';

class DriveTrackingService {
  DriveTrackingService(this._api);

  final ApiClient _api;
  final List<Map<String, dynamic>> _buffer = [];
  final _positions = StreamController<Position>.broadcast();
  StreamSubscription<Position>? _subscription;
  int? _recordId;
  int _nextSequence = 0;

  int? get recordId => _recordId;
  bool get isRecording => _recordId != null;
  Stream<Position> get positions => _positions.stream;

  Future<bool> ensurePermission() async {
    if (!await Geolocator.isLocationServiceEnabled()) return false;
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    return permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse;
  }

  Future<Position> currentPosition() async {
    if (!await ensurePermission()) {
      throw StateError('위치 권한과 GPS를 켜 주세요.');
    }
    return Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.bestForNavigation,
      ),
    );
  }

  Future<int> start({
    int? courseId,
    int? crewCourseId,
    int? lightningCourseId,
  }) async {
    if (isRecording) throw StateError('이미 주행을 기록하고 있습니다.');
    if (!await ensurePermission()) {
      throw StateError('위치 권한과 GPS를 켜 주세요.');
    }
    final json = await _api.post('/drive-records', body: {
      'course_id': courseId,
      'crew_course_id': crewCourseId,
      'lightning_course_id': lightningCourseId,
      'started_at': DateTime.now().toUtc().toIso8601String(),
    }) as Map<String, dynamic>;
    _recordId = json['id'] as int;
    _nextSequence = 0;
    _buffer.clear();
    final settings = Platform.isAndroid
        ? AndroidSettings(
            accuracy: LocationAccuracy.bestForNavigation,
            distanceFilter: 10,
            intervalDuration: const Duration(seconds: 5),
            foregroundNotificationConfig: const ForegroundNotificationConfig(
              notificationTitle: 'WayPoint 주행 기록 중',
              notificationText: '안전한 주행 기록을 위해 GPS를 수집하고 있습니다.',
              enableWakeLock: true,
            ),
          )
        : const LocationSettings(
            accuracy: LocationAccuracy.bestForNavigation,
            distanceFilter: 10,
          );
    _subscription = Geolocator.getPositionStream(locationSettings: settings)
        .listen(_onPosition);
    return _recordId!;
  }

  void _onPosition(Position position) {
    _positions.add(position);
    _buffer.add({
      'sequence': _nextSequence++,
      'latitude': position.latitude,
      'longitude': position.longitude,
      'recorded_at': position.timestamp.toUtc().toIso8601String(),
      'accuracy_meters': position.accuracy,
      'speed_mps': position.speed < 0 ? null : position.speed,
      'heading_degrees': position.heading < 0 ? null : position.heading,
    });
    if (_buffer.length >= 20) unawaited(flush());
  }

  Future<void> flush() async {
    if (_recordId == null || _buffer.isEmpty) return;
    final points = List<Map<String, dynamic>>.from(_buffer);
    _buffer.removeRange(0, points.length);
    try {
      await _api.post('/drive-records/$_recordId/points', body: {'points': points});
    } catch (_) {
      _buffer.insertAll(0, points);
      rethrow;
    }
  }

  Future<Map<String, dynamic>> complete() async {
    await _subscription?.cancel();
    await flush();
    final id = _recordId;
    if (id == null) throw StateError('진행 중인 주행이 없습니다.');
    final result = await _api.post('/drive-records/$id/complete', body: {
      'completed_at': DateTime.now().toUtc().toIso8601String(),
    }) as Map<String, dynamic>;
    _reset();
    return result;
  }

  Future<void> cancel() async {
    await _subscription?.cancel();
    final id = _recordId;
    if (id != null) await _api.post('/drive-records/$id/cancel');
    _reset();
  }

  void _reset() {
    _recordId = null;
    _buffer.clear();
    _subscription = null;
  }

  Future<void> dispose() async {
    await _subscription?.cancel();
    await _positions.close();
  }
}
