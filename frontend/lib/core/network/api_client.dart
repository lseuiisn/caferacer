import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../config/app_environment.dart';

class ApiException implements Exception {
  const ApiException(this.statusCode, this.message);
  final int statusCode;
  final String message;
  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({required this.accessToken, http.Client? client})
    : _client = client ?? http.Client();
  final String? Function() accessToken;
  final http.Client _client;

  Uri uri(String path, [Map<String, String>? query]) =>
      Uri.parse('${AppEnvironment.apiBaseUrl}$path')
          .replace(queryParameters: query);

  Map<String, String> get headers {
    final token = accessToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<dynamic> get(String path, {Map<String, String>? query}) async =>
      _decode(await _client.get(uri(path, query), headers: headers));
  Future<T> getAs<T>(String path, {Map<String, String>? query}) async =>
      await get(path, query: query) as T;
  Future<dynamic> getWithQueryAll(
    String path,
    Map<String, List<String>> query,
  ) async {
    final target = Uri.parse('${AppEnvironment.apiBaseUrl}$path')
        .replace(queryParameters: query);
    return _decode(await _client.get(target, headers: headers));
  }
  Future<dynamic> post(String path, {Object? body}) async => _decode(
    await _client.post(uri(path), headers: headers,
        body: body == null ? null : jsonEncode(body)),
  );
  Future<dynamic> patch(String path, {Object? body}) async => _decode(
    await _client.patch(uri(path), headers: headers, body: jsonEncode(body)),
  );
  Future<dynamic> put(String path, {Object? body}) async => _decode(
    await _client.put(uri(path), headers: headers, body: jsonEncode(body)),
  );
  Future<dynamic> delete(String path) async =>
      _decode(await _client.delete(uri(path), headers: headers));

  Future<String> uploadImage(File file) async {
    final extension = file.path.split('.').last.toLowerCase();
    final subtype = switch (extension) {
      'jpg' || 'jpeg' => 'jpeg',
      'png' => 'png',
      'webp' => 'webp',
      _ => throw const ApiException(415, 'JPEG, PNG, WebP 이미지만 업로드할 수 있습니다.'),
    };
    final request = http.MultipartRequest('POST', uri('/uploads/images'));
    final token = accessToken();
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    request.files.add(await http.MultipartFile.fromPath(
      'file',
      file.path,
      contentType: MediaType('image', subtype),
    ));
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    final decoded = _decode(response) as Map<String, dynamic>;
    return decoded['url'].toString();
  }

  dynamic _decode(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      var message = response.body;
      try {
        message = (jsonDecode(response.body) as Map<String, dynamic>)['detail']
            .toString();
      } catch (_) {}
      throw ApiException(response.statusCode, message);
    }
    return response.body.isEmpty ? null : jsonDecode(response.body);
  }
}
