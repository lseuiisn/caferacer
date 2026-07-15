import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/storage/session_store.dart';
import '../domain/auth_repository.dart';
import '../domain/social_auth_result.dart';
import 'api_config.dart';

class AuthApiException implements Exception {
  AuthApiException(this.statusCode, this.message);
  final int statusCode;
  final String message;
  @override
  String toString() => message;
}

class HttpAuthRepository implements AuthRepository {
  HttpAuthRepository(this._sessionStore, {http.Client? client})
    : _client = client ?? http.Client();

  final http.Client _client;
  final SessionStore _sessionStore;
  Uri _uri(String path) => Uri.parse('${ApiConfig.baseUrl}$path');

  @override
  Future<AppSession> exchangeToken(SocialAuthResult socialResult) async {
    final login = await _client.post(
      _uri('/auth/social/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'provider': socialResult.provider.name,
        'provider_credential': socialResult.providerToken,
        'device_name': null,
      }),
    );
    if (login.statusCode != 200) {
      throw AuthApiException(login.statusCode, _detail(login.body));
    }
    final tokens = jsonDecode(login.body) as Map<String, dynamic>;
    return _loadMeAndSave(
      tokens['access_token'] as String,
      tokens['refresh_token'] as String?,
    );
  }

  Future<AppSession> _loadMeAndSave(
    String accessToken,
    String? refreshToken,
  ) async {
    final response = await _client.get(
      _uri('/auth/me'),
      headers: {'Authorization': 'Bearer $accessToken'},
    );
    if (response.statusCode != 200) {
      throw AuthApiException(response.statusCode, _detail(response.body));
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final session = AppSession(
      userId: json['id'].toString(),
      accessToken: accessToken,
      refreshToken: refreshToken,
      nickname: json['nickname'] as String?,
      role: json['role'] as String?,
    );
    await _sessionStore.save(session);
    return session;
  }

  @override
  Future<void> logout() async {
    final session = await _sessionStore.read();
    try {
      if (session?.refreshToken != null) {
        await _client.post(
          _uri('/auth/logout'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh_token': session!.refreshToken}),
        );
      }
    } finally {
      await _sessionStore.clear();
    }
  }

  @override
  Future<AppSession?> restoreSession() async {
    final stored = await _sessionStore.read();
    if (stored?.refreshToken == null) return null;
    try {
      final response = await _client.post(
        _uri('/auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': stored!.refreshToken}),
      );
      if (response.statusCode != 200) throw StateError('refresh failed');
      final tokens = jsonDecode(response.body) as Map<String, dynamic>;
      return _loadMeAndSave(
        tokens['access_token'] as String,
        tokens['refresh_token'] as String?,
      );
    } catch (_) {
      await _sessionStore.clear();
      return null;
    }
  }

  String _detail(String body) {
    try {
      return (jsonDecode(body) as Map<String, dynamic>)['detail']?.toString() ??
          body;
    } catch (_) {
      return body;
    }
  }
}
