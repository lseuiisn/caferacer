import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../features/auth/domain/auth_repository.dart';

class SessionStore {
  SessionStore({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  static const _key = 'waypoint_session';
  final FlutterSecureStorage _storage;

  Future<void> save(AppSession session) => _storage.write(
    key: _key,
    value: jsonEncode({
      'user_id': session.userId,
      'access_token': session.accessToken,
      'refresh_token': session.refreshToken,
      'nickname': session.nickname,
      'role': session.role,
    }),
  );

  Future<AppSession?> read() async {
    final raw = await _storage.read(key: _key);
    if (raw == null) return null;
    try {
      final json = jsonDecode(raw) as Map<String, dynamic>;
      return AppSession(
        userId: json['user_id'].toString(),
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String?,
        nickname: json['nickname'] as String?,
        role: json['role'] as String?,
      );
    } catch (_) {
      await clear();
      return null;
    }
  }

  Future<void> clear() => _storage.delete(key: _key);
}
