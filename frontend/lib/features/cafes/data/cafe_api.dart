import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../auth/data/api_config.dart';
import '../domain/cafe.dart';
import '../domain/page_meta.dart';

class CafePageResult {
  final List<Cafe> items;
  final PageMeta meta;
  const CafePageResult({required this.items, required this.meta});
}

class CafeApiException implements Exception {
  final int statusCode;
  final String message;
  CafeApiException(this.statusCode, this.message);

  @override
  String toString() => 'CafeApiException($statusCode): $message';
}

class CafeApi {
  CafeApi({http.Client? client}) : _client = client ?? http.Client();
  final http.Client _client;

  Future<CafePageResult> fetchCafes({int page = 1, int size = 20}) async {
    final uri = Uri.parse(
      '${ApiConfig.baseUrl}/cafes',
    ).replace(queryParameters: {'page': '$page', 'size': '$size'});

    final res = await _client.get(uri);
    if (res.statusCode != 200) {
      throw CafeApiException(res.statusCode, res.body);
    }

    final json = jsonDecode(res.body) as Map<String, dynamic>;
    final items = (json['items'] as List<dynamic>)
        .map((e) => Cafe.fromJson(e as Map<String, dynamic>))
        .toList();
    return CafePageResult(
      items: items,
      meta: PageMeta.fromJson(json['meta'] as Map<String, dynamic>),
    );
  }

  Future<Map<String, dynamic>> fetchCafeDetail(int cafeId) async {
    final res = await _client.get(Uri.parse('${ApiConfig.baseUrl}/cafes/$cafeId'));
    if (res.statusCode != 200) {
      throw CafeApiException(res.statusCode, res.body);
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}
