import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../shared/widgets/tmap_native_map.dart';
import '../../auth/providers.dart';
import '../../drive_tracking/providers.dart';

class CafeListScreen extends ConsumerStatefulWidget {
  const CafeListScreen({super.key});

  @override
  ConsumerState<CafeListScreen> createState() => _CafeListScreenState();
}

class _CafeListScreenState extends ConsumerState<CafeListScreen> {
  bool? _parking;
  final Set<String> _prices = {};
  final Set<String> _tags = {};
  bool _favoritesOnly = false;
  bool _showList = false;
  late Future<_CafeData> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = _load();
  }

  Future<_CafeData> _load() async {
    final api = ref.read(apiClientProvider);
    final position = await ref.read(driveTrackingServiceProvider).currentPosition();
    final results = await Future.wait([
      api.getWithQueryAll('/cafes', {
        'page': ['1'],
        'size': ['50'],
        if (_parking != null) 'parking': ['$_parking'],
        if (_prices.isNotEmpty) 'price_ranges': _prices.toList(),
        if (_tags.isNotEmpty) 'tags': _tags.toList(),
      }),
      api.get('/me/favorites'),
    ]);
    final page = results[0] as Map<String, dynamic>;
    final favorites = (results[1] as List<dynamic>)
        .map((item) => (item as Map<String, dynamic>)['id'] as int)
        .toSet();
    var items = (page['items'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    for (final item in items) {
      item['distance_meters'] = Geolocator.distanceBetween(
        position.latitude,
        position.longitude,
        (item['latitude'] as num).toDouble(),
        (item['longitude'] as num).toDouble(),
      ).round();
    }
    items.sort((a, b) =>
        (a['distance_meters'] as int).compareTo(b['distance_meters'] as int));
    if (_favoritesOnly) items = items.where((item) => favorites.contains(item['id'])).toList();
    return _CafeData(items, favorites, position.latitude, position.longitude);
  }

  Future<void> _filters() async {
    var parking = _parking;
    final prices = Set<String>.from(_prices);
    final tags = Set<String>.from(_tags);
    final applied = await showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      builder: (context) => StatefulBuilder(builder: (context, setState) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('카페 필터', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Wrap(spacing: 8, children: [
            ChoiceChip(label: const Text('주차 전체'), selected: parking == null, onSelected: (_) => setState(() => parking = null)),
            ChoiceChip(label: const Text('주차 가능'), selected: parking == true, onSelected: (_) => setState(() => parking = true)),
          ]),
          const SizedBox(height: 12),
          const Text('가격대'),
          Wrap(spacing: 8, children: ['low', 'medium', 'high'].map((value) => FilterChip(
            label: Text({'low': '저렴', 'medium': '보통', 'high': '높음'}[value]!),
            selected: prices.contains(value),
            onSelected: (selected) => setState(() => selected ? prices.add(value) : prices.remove(value)),
          )).toList()),
          const SizedBox(height: 12),
          const Text('키워드'),
          Wrap(spacing: 8, runSpacing: 4, children: {
            'scenic_view': '뷰 맛집', 'riverside': '강변', 'large': '대형',
            'bakery': '베이커리', 'pet_friendly': '반려동물',
          }.entries.map((entry) => FilterChip(
            label: Text(entry.value),
            selected: tags.contains(entry.key),
            onSelected: (selected) => setState(() => selected ? tags.add(entry.key) : tags.remove(entry.key)),
          )).toList()),
          const SizedBox(height: 20),
          SizedBox(width: double.infinity, child: FilledButton(
            onPressed: () => Navigator.pop(context, true), child: const Text('적용'),
          )),
        ]),
      )),
    );
    if (applied == true) {
      setState(() {
        _parking = parking;
        _prices
          ..clear()
          ..addAll(prices);
        _tags
          ..clear()
          ..addAll(tags);
        _reload();
      });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('주변 추천 카페'),
      actions: [
        IconButton(onPressed: _filters, tooltip: '필터', icon: const Icon(Icons.tune)),
        IconButton(
          onPressed: () => setState(() => _showList = !_showList),
          tooltip: _showList ? '지도 보기' : '목록 보기',
          icon: Icon(_showList ? Icons.map_outlined : Icons.list),
        ),
      ],
    ),
    body: FutureBuilder<_CafeData>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) return Center(child: Text('${snapshot.error}'));
        final data = snapshot.data!;
        return Column(children: [
          SizedBox(
            height: 48,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
              FilterChip(
                avatar: const Icon(Icons.star, size: 18),
                label: const Text('즐겨찾기'),
                selected: _favoritesOnly,
                onSelected: (value) => setState(() {
                  _favoritesOnly = value;
                  _reload();
                }),
              ),
              if (_parking == true) const Padding(padding: EdgeInsets.only(left: 8), child: Chip(label: Text('주차 가능'))),
              ..._prices.map((value) => Padding(padding: const EdgeInsets.only(left: 8), child: Chip(label: Text(value)))),
              ..._tags.map((value) => Padding(padding: const EdgeInsets.only(left: 8), child: Chip(label: Text(value)))),
            ]),
          ),
          Expanded(child: data.items.isEmpty
              ? const Center(child: Text('선택한 조건의 카페가 없습니다.'))
              : _showList
                  ? _CafeList(data: data, onTap: (cafe) => _detail(cafe, data))
                  : _CafeMap(data: data, onTap: (cafe) => _detail(cafe, data))),
        ]);
      },
    ),
  );

  Future<void> _detail(Map<String, dynamic> cafe, _CafeData data) async {
    final detailFuture = ref.read(apiClientProvider).get('/cafes/${cafe['id']}');
    final navigationFuture = ref.read(apiClientProvider).post(
      '/cafes/${cafe['id']}/navigation',
      body: {
        'origin': {
          'latitude': data.currentLatitude,
          'longitude': data.currentLongitude,
        },
      },
    );
    var favorite = data.favoriteIds.contains(cafe['id']);
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => FutureBuilder<dynamic>(
        future: detailFuture,
        builder: (context, snapshot) => StatefulBuilder(builder: (context, setState) {
          final detail = snapshot.data as Map<String, dynamic>? ?? cafe;
          final images = (detail['images'] as List<dynamic>? ?? []).map((item) {
            if (item is String) return item;
            return (item as Map<String, dynamic>)['image_url'].toString();
          }).toList();
          return SafeArea(child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(detail['name'].toString(), style: Theme.of(context).textTheme.titleLarge)),
                IconButton(
                  onPressed: () async {
                    final api = ref.read(apiClientProvider);
                    favorite
                        ? await api.delete('/cafes/${cafe['id']}/favorite')
                        : await api.put('/cafes/${cafe['id']}/favorite');
                    setState(() => favorite = !favorite);
                    this.setState(_reload);
                  },
                  icon: Icon(favorite ? Icons.star : Icons.star_border, color: Colors.amber),
                ),
              ]),
              if (images.isNotEmpty)
                SizedBox(height: 220, child: PageView(children: images.map((url) => Image.network(url, fit: BoxFit.cover)).toList())),
              const SizedBox(height: 8),
              Text(detail['address'].toString()),
              FutureBuilder<dynamic>(
                future: navigationFuture,
                builder: (context, routeSnapshot) {
                  final route = routeSnapshot.data as Map<String, dynamic>?;
                  if (route == null) return const SizedBox.shrink();
                  return Text(
                    '현재 위치에서 ${((route['distance_meters'] as num) / 1000).toStringAsFixed(1)}km · '
                    '약 ${((route['duration_seconds'] as num) / 60).ceil()}분',
                  );
                },
              ),
              Text('주차 ${detail['parking_available'] == true ? '가능' : '정보 없음'} · '
                  '가격대 ${detail['price_range'] ?? '정보 없음'}'),
              if (detail['business_hours'] != null) Text('영업시간 ${detail['business_hours']}'),
              if (detail['phone_number'] != null) Text('전화 ${detail['phone_number']}'),
              Wrap(spacing: 6, children: (detail['tags'] as List<dynamic>? ?? []).map((tag) => Chip(label: Text(tag.toString()))).toList()),
              SizedBox(width: double.infinity, child: OutlinedButton.icon(
                onPressed: () => launchUrl(
                  Uri.parse('https://map.naver.com/p/search/${Uri.encodeComponent(detail['name'].toString())}'),
                  mode: LaunchMode.externalApplication,
                ),
                icon: const Icon(Icons.open_in_new),
                label: const Text('네이버 지도에서 보기'),
              )),
            ]),
          ));
        }),
      ),
    );
  }
}

class _CafeData {
  const _CafeData(
    this.items,
    this.favoriteIds,
    this.currentLatitude,
    this.currentLongitude,
  );
  final List<Map<String, dynamic>> items;
  final Set<int> favoriteIds;
  final double currentLatitude;
  final double currentLongitude;
}

class _CafeList extends StatelessWidget {
  const _CafeList({required this.data, required this.onTap});
  final _CafeData data;
  final ValueChanged<Map<String, dynamic>> onTap;

  @override
  Widget build(BuildContext context) => ListView.builder(
    itemCount: data.items.length,
    itemBuilder: (_, index) {
      final cafe = data.items[index];
      return ListTile(
        leading: cafe['thumbnail_url'] == null
            ? const CircleAvatar(child: Icon(Icons.local_cafe))
            : CircleAvatar(backgroundImage: NetworkImage(cafe['thumbnail_url'].toString())),
        title: Text(cafe['name'].toString()),
        subtitle: Text(
          '${cafe['address']} · ${_distance(cafe['distance_meters'] as int)}',
        ),
        trailing: Icon(data.favoriteIds.contains(cafe['id']) ? Icons.star : Icons.chevron_right,
            color: data.favoriteIds.contains(cafe['id']) ? Colors.amber : null),
        onTap: () => onTap(cafe),
      );
    },
  );

  String _distance(int meters) => meters < 1000
      ? '${meters}m'
      : '${(meters / 1000).toStringAsFixed(1)}km';
}

class _CafeMap extends StatelessWidget {
  const _CafeMap({required this.data, required this.onTap});
  final _CafeData data;
  final ValueChanged<Map<String, dynamic>> onTap;

  @override
  Widget build(BuildContext context) {
    if (Platform.isAndroid) {
      return TmapNativeMap(
        centerLatitude: data.currentLatitude,
        centerLongitude: data.currentLongitude,
        markers: [
          TmapNativeMarker(
            id: 'current',
            latitude: data.currentLatitude,
            longitude: data.currentLongitude,
            title: '현재 위치',
            color: 'start',
          ),
          ...data.items.map((cafe) => TmapNativeMarker(
          id: 'cafe:${cafe['id']}',
          latitude: (cafe['latitude'] as num).toDouble(),
          longitude: (cafe['longitude'] as num).toDouble(),
          title: cafe['name'].toString(),
          subtitle: cafe['address'].toString(),
          color: 'cafe',
          )),
        ],
        onMarkerTap: (id) {
          if (id == 'current') return;
          final target = data.items.where((cafe) => cafe['id'].toString() == id.split(':').last).firstOrNull;
          if (target != null) onTap(target);
        },
      );
    }
    return FlutterMap(
      options: MapOptions(
        initialCenter: LatLng(data.currentLatitude, data.currentLongitude),
        initialZoom: 11,
      ),
      children: [
        TileLayer(urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', userAgentPackageName: 'com.waypoint.app'),
        MarkerLayer(markers: [
          Marker(
            point: LatLng(data.currentLatitude, data.currentLongitude),
            width: 48,
            height: 48,
            child: const Icon(Icons.my_location, color: Colors.blue),
          ),
          ...data.items.map((cafe) => Marker(
          point: LatLng((cafe['latitude'] as num).toDouble(), (cafe['longitude'] as num).toDouble()),
          width: 48, height: 48,
          child: IconButton(onPressed: () => onTap(cafe), icon: const Icon(Icons.location_on, color: Colors.red)),
          )),
        ]),
        const RichAttributionWidget(attributions: [TextSourceAttribution('OpenStreetMap contributors')]),
      ],
    );
  }
}
