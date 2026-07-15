import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../app/theme/app_theme.dart';
import '../../../shared/widgets/tmap_native_map.dart';
import '../../auth/providers.dart';
import '../../drive_tracking/providers.dart';

class CafeFinderScreen extends ConsumerStatefulWidget {
  const CafeFinderScreen({this.isActive = true, super.key});

  final bool isActive;

  @override
  ConsumerState<CafeFinderScreen> createState() => _CafeFinderScreenState();
}

class _CafeFinderScreenState extends ConsumerState<CafeFinderScreen> {
  final _searchController = TextEditingController();
  bool? _parking;
  final Set<String> _prices = {};
  final Set<String> _tags = {};
  bool _favoritesOnly = false;
  bool _showList = false;
  String _query = '';
  Map<String, dynamic>? _selectedCafe;
  late Future<_CafeData> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _reload() {
    _future = _load();
  }

  Future<_CafeData> _load() async {
    final api = ref.read(apiClientProvider);
    final position = await ref
        .read(driveTrackingServiceProvider)
        .currentPosition();
    final responses = await Future.wait([
      api.getWithQueryAll('/cafes', {
        'page': ['1'],
        'size': ['50'],
        if (_parking != null) 'parking': ['$_parking'],
        if (_prices.isNotEmpty) 'price_ranges': _prices.toList(),
        if (_tags.isNotEmpty) 'tags': _tags.toList(),
      }),
      api.get('/me/favorites'),
    ]);
    final page = responses[0] as Map<String, dynamic>;
    final favoriteIds = (responses[1] as List<dynamic>)
        .map((raw) => (raw as Map<String, dynamic>)['id'] as int)
        .toSet();
    var cafes = (page['items'] as List<dynamic>? ?? const [])
        .cast<Map<String, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    for (final cafe in cafes) {
      cafe['distance_meters'] = Geolocator.distanceBetween(
        position.latitude,
        position.longitude,
        (cafe['latitude'] as num).toDouble(),
        (cafe['longitude'] as num).toDouble(),
      ).round();
    }
    cafes.sort(
      (a, b) =>
          (a['distance_meters'] as int).compareTo(b['distance_meters'] as int),
    );
    if (_favoritesOnly) {
      cafes = cafes.where((cafe) => favoriteIds.contains(cafe['id'])).toList();
    }
    final normalizedQuery = _query.trim().toLowerCase();
    if (normalizedQuery.isNotEmpty) {
      cafes = cafes.where((cafe) {
        final text = '${cafe['name']} ${cafe['address']}'.toLowerCase();
        return text.contains(normalizedQuery);
      }).toList();
    }
    return _CafeData(
      items: cafes,
      favoriteIds: favoriteIds,
      currentLatitude: position.latitude,
      currentLongitude: position.longitude,
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: FutureBuilder<_CafeData>(
      future: _future,
      builder: (context, snapshot) {
        final data = snapshot.data;
        return Stack(
          children: [
            Positioned.fill(
              child: snapshot.connectionState != ConnectionState.done
                  ? const Center(child: CircularProgressIndicator())
                  : snapshot.hasError
                  ? _CafeMessage(
                      icon: Icons.cloud_off_outlined,
                      message: '카페를 불러오지 못했습니다.\n${snapshot.error}',
                    )
                  : data!.items.isEmpty
                  ? const _CafeMessage(
                      icon: Icons.local_cafe_outlined,
                      message: '조건에 맞는 카페가 없습니다.',
                    )
                  : _showList
                  ? _CafeResultList(
                      data: data,
                      onTap: (cafe) => _openDetail(cafe, data),
                    )
                  : _CafeMap(
                      data: data,
                      isActive: widget.isActive,
                      onTap: (cafe) => setState(() => _selectedCafe = cafe),
                    ),
            ),
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: SafeArea(
                bottom: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: _CafeFinderHeader(
                    searchController: _searchController,
                    favoritesOnly: _favoritesOnly,
                    parkingOnly: _parking == true,
                    filterCount: _prices.length + _tags.length,
                    showList: _showList,
                    onSearch: _search,
                    onClearSearch: _clearSearch,
                    onToggleFavorite: (selected) => setState(() {
                      _favoritesOnly = selected;
                      _selectedCafe = null;
                      _reload();
                    }),
                    onToggleParking: (selected) => setState(() {
                      _parking = selected ? true : null;
                      _selectedCafe = null;
                      _reload();
                    }),
                    onOpenFilters: _openFilters,
                    onToggleView: () => setState(() {
                      _showList = !_showList;
                      _selectedCafe = null;
                    }),
                  ),
                ),
              ),
            ),
            if (!_showList && data != null && _selectedCafe != null)
              Positioned(
                left: 16,
                right: 16,
                bottom: 16,
                child: _CafePreviewCard(
                  cafe: _selectedCafe!,
                  favorite: data.favoriteIds.contains(_selectedCafe!['id']),
                  onFavorite: () => _toggleFavorite(_selectedCafe!, data),
                  onTap: () => _openDetail(_selectedCafe!, data),
                  onClose: () => setState(() => _selectedCafe = null),
                ),
              ),
          ],
        );
      },
    ),
  );

  void _search(String value) {
    setState(() {
      _query = value.trim();
      _selectedCafe = null;
      _reload();
    });
  }

  void _clearSearch() {
    _searchController.clear();
    _search('');
  }

  Future<void> _toggleFavorite(
    Map<String, dynamic> cafe,
    _CafeData data,
  ) async {
    final id = cafe['id'] as int;
    final favorite = data.favoriteIds.contains(id);
    final api = ref.read(apiClientProvider);
    favorite
        ? await api.delete('/cafes/$id/favorite')
        : await api.put('/cafes/$id/favorite');
    if (!mounted) return;
    setState(() {
      favorite ? data.favoriteIds.remove(id) : data.favoriteIds.add(id);
    });
  }

  Future<void> _openFilters() async {
    var parking = _parking;
    final prices = Set<String>.from(_prices);
    final tags = Set<String>.from(_tags);
    final applied = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 4, 24, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('카페 필터', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 18),
                const Text('주차', style: TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    ChoiceChip(
                      label: const Text('전체'),
                      selected: parking == null,
                      onSelected: (_) => setSheetState(() => parking = null),
                    ),
                    ChoiceChip(
                      label: const Text('주차 가능'),
                      selected: parking == true,
                      onSelected: (_) => setSheetState(() => parking = true),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                const Text(
                  '가격대',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: const {'low': '부담 없음', 'medium': '보통', 'high': '높음'}
                      .entries
                      .map(
                        (entry) => FilterChip(
                          label: Text(entry.value),
                          selected: prices.contains(entry.key),
                          onSelected: (selected) => setSheetState(() {
                            selected
                                ? prices.add(entry.key)
                                : prices.remove(entry.key);
                          }),
                        ),
                      )
                      .toList(),
                ),
                const SizedBox(height: 18),
                const Text(
                  '키워드',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children:
                      const {
                            'scenic_view': '뷰 맛집',
                            'riverside': '강변',
                            'large': '대형',
                            'bakery': '베이커리',
                            'pet_friendly': '반려동물',
                          }.entries
                          .map(
                            (entry) => FilterChip(
                              label: Text(entry.value),
                              selected: tags.contains(entry.key),
                              onSelected: (selected) => setSheetState(() {
                                selected
                                    ? tags.add(entry.key)
                                    : tags.remove(entry.key);
                              }),
                            ),
                          )
                          .toList(),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.lime,
                      foregroundColor: AppColors.ink,
                      side: const BorderSide(color: AppColors.ink),
                    ),
                    child: const Text('필터 적용'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    if (applied != true || !mounted) return;
    setState(() {
      _parking = parking;
      _prices
        ..clear()
        ..addAll(prices);
      _tags
        ..clear()
        ..addAll(tags);
      _selectedCafe = null;
      _reload();
    });
  }

  Future<void> _openDetail(Map<String, dynamic> cafe, _CafeData data) async {
    final detailFuture = ref
        .read(apiClientProvider)
        .get('/cafes/${cafe['id']}');
    final navigationFuture = ref
        .read(apiClientProvider)
        .post(
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
      isScrollControlled: true,
      builder: (sheetContext) => FutureBuilder<dynamic>(
        future: detailFuture,
        builder: (context, snapshot) {
          final detail = snapshot.data as Map<String, dynamic>? ?? cafe;
          final images = (detail['images'] as List<dynamic>? ?? const [])
              .map(
                (raw) => raw is String
                    ? raw
                    : (raw as Map<String, dynamic>)['image_url'].toString(),
              )
              .where((url) => url.isNotEmpty)
              .toList();
          return StatefulBuilder(
            builder: (context, setSheetState) => SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(24, 4, 24, 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            detail['name'].toString(),
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                        ),
                        IconButton(
                          tooltip: favorite ? '즐겨찾기 해제' : '즐겨찾기',
                          onPressed: () async {
                            await _toggleFavorite(cafe, data);
                            setSheetState(() => favorite = !favorite);
                          },
                          style: IconButton.styleFrom(
                            backgroundColor: favorite
                                ? AppColors.lime
                                : AppColors.canvas,
                          ),
                          icon: Icon(favorite ? Icons.star : Icons.star_border),
                        ),
                      ],
                    ),
                    if (images.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: SizedBox(
                          height: 220,
                          child: PageView(
                            children: images
                                .map(
                                  (url) =>
                                      Image.network(url, fit: BoxFit.cover),
                                )
                                .toList(),
                          ),
                        ),
                      ),
                    ],
                    const SizedBox(height: 16),
                    Text(detail['address']?.toString() ?? '주소 정보 없음'),
                    const SizedBox(height: 8),
                    FutureBuilder<dynamic>(
                      future: navigationFuture,
                      builder: (context, routeSnapshot) {
                        final route =
                            routeSnapshot.data as Map<String, dynamic>?;
                        if (route == null) return const SizedBox.shrink();
                        return Text(
                          '현재 위치에서 ${_distance(route['distance_meters'] as num)} · 약 ${((route['duration_seconds'] as num) / 60).ceil()}분',
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        );
                      },
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Chip(
                          label: Text(
                            detail['parking_available'] == true
                                ? '주차 가능'
                                : '주차 정보 없음',
                          ),
                        ),
                        if (detail['price_range'] != null)
                          Chip(label: Text('가격 ${detail['price_range']}')),
                        ...(detail['tags'] as List<dynamic>? ?? const []).map(
                          (tag) => Chip(label: Text(tag.toString())),
                        ),
                      ],
                    ),
                    if (detail['business_hours'] != null) ...[
                      const SizedBox(height: 12),
                      Text('영업시간  ${detail['business_hours']}'),
                    ],
                    if (detail['phone_number'] != null)
                      Text('전화  ${detail['phone_number']}'),
                    const SizedBox(height: 22),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: () => launchUrl(
                          Uri.parse(
                            'https://map.naver.com/p/search/${Uri.encodeComponent(detail['name'].toString())}',
                          ),
                          mode: LaunchMode.externalApplication,
                        ),
                        icon: const Icon(Icons.open_in_new),
                        label: const Text('네이버 지도에서 보기'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _CafeFinderHeader extends StatelessWidget {
  const _CafeFinderHeader({
    required this.searchController,
    required this.favoritesOnly,
    required this.parkingOnly,
    required this.filterCount,
    required this.showList,
    required this.onSearch,
    required this.onClearSearch,
    required this.onToggleFavorite,
    required this.onToggleParking,
    required this.onOpenFilters,
    required this.onToggleView,
  });

  final TextEditingController searchController;
  final bool favoritesOnly;
  final bool parkingOnly;
  final int filterCount;
  final bool showList;
  final ValueChanged<String> onSearch;
  final VoidCallback onClearSearch;
  final ValueChanged<bool> onToggleFavorite;
  final ValueChanged<bool> onToggleParking;
  final VoidCallback onOpenFilters;
  final VoidCallback onToggleView;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
    decoration: BoxDecoration(
      color: AppColors.surface.withValues(alpha: 0.96),
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: AppColors.ink, width: 1.2),
      boxShadow: const [
        BoxShadow(
          color: Color(0x22000000),
          blurRadius: 18,
          offset: Offset(0, 7),
        ),
      ],
    ),
    child: Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'WAYPOINT',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1.8,
                    ),
                  ),
                  Text(
                    '카페 찾기',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ],
              ),
            ),
            _HeaderIconButton(
              tooltip: showList ? '지도 보기' : '목록 보기',
              icon: showList ? Icons.map_outlined : Icons.view_list,
              onPressed: onToggleView,
            ),
          ],
        ),
        const SizedBox(height: 12),
        TextField(
          controller: searchController,
          textInputAction: TextInputAction.search,
          onSubmitted: onSearch,
          decoration: InputDecoration(
            hintText: '카페 이름이나 지역을 검색해보세요',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: searchController.text.isEmpty
                ? null
                : IconButton(
                    tooltip: '검색어 지우기',
                    onPressed: onClearSearch,
                    icon: const Icon(Icons.close),
                  ),
          ),
        ),
        const SizedBox(height: 10),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              FilterChip(
                avatar: const Icon(Icons.star_outline, size: 17),
                label: const Text('즐겨찾기'),
                selected: favoritesOnly,
                onSelected: onToggleFavorite,
              ),
              const SizedBox(width: 8),
              FilterChip(
                avatar: const Icon(Icons.local_parking_outlined, size: 17),
                label: const Text('주차 가능'),
                selected: parkingOnly,
                onSelected: onToggleParking,
              ),
              const SizedBox(width: 8),
              ActionChip(
                avatar: const Icon(Icons.tune, size: 17),
                label: Text(filterCount == 0 ? '필터' : '필터 $filterCount'),
                onPressed: onOpenFilters,
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _HeaderIconButton extends StatelessWidget {
  const _HeaderIconButton({
    required this.tooltip,
    required this.icon,
    required this.onPressed,
  });

  final String tooltip;
  final IconData icon;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => IconButton(
    tooltip: tooltip,
    onPressed: onPressed,
    style: IconButton.styleFrom(
      backgroundColor: AppColors.ink,
      foregroundColor: Colors.white,
      fixedSize: const Size(44, 44),
    ),
    icon: Icon(icon),
  );
}

class _CafeData {
  const _CafeData({
    required this.items,
    required this.favoriteIds,
    required this.currentLatitude,
    required this.currentLongitude,
  });

  final List<Map<String, dynamic>> items;
  final Set<int> favoriteIds;
  final double currentLatitude;
  final double currentLongitude;
}

class _CafeMap extends StatelessWidget {
  const _CafeMap({
    required this.data,
    required this.isActive,
    required this.onTap,
  });

  final _CafeData data;
  final bool isActive;
  final ValueChanged<Map<String, dynamic>> onTap;

  @override
  Widget build(BuildContext context) {
    if (Platform.isAndroid) {
      if (!isActive) return const SizedBox.shrink();
      return TmapNativeMap(
        centerLatitude: data.currentLatitude,
        centerLongitude: data.currentLongitude,
        zoom: 11,
        markers: [
          TmapNativeMarker(
            id: 'current',
            latitude: data.currentLatitude,
            longitude: data.currentLongitude,
            title: '현재 위치',
            color: 'start',
          ),
          ...data.items.map(
            (cafe) => TmapNativeMarker(
              id: 'cafe:${cafe['id']}',
              latitude: (cafe['latitude'] as num).toDouble(),
              longitude: (cafe['longitude'] as num).toDouble(),
              title: cafe['name'].toString(),
              subtitle: cafe['address']?.toString() ?? '',
              color: 'cafe',
            ),
          ),
        ],
        onMarkerTap: (id) {
          if (id == 'current') return;
          final cafeId = id.split(':').last;
          final cafe = data.items
              .where((item) => item['id'].toString() == cafeId)
              .firstOrNull;
          if (cafe != null) onTap(cafe);
        },
      );
    }
    return FlutterMap(
      options: MapOptions(
        initialCenter: LatLng(data.currentLatitude, data.currentLongitude),
        initialZoom: 11,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.waypoint.app',
        ),
        MarkerLayer(
          markers: [
            Marker(
              point: LatLng(data.currentLatitude, data.currentLongitude),
              width: 44,
              height: 44,
              child: const Icon(Icons.my_location, color: AppColors.blue),
            ),
            ...data.items.map(
              (cafe) => Marker(
                point: LatLng(
                  (cafe['latitude'] as num).toDouble(),
                  (cafe['longitude'] as num).toDouble(),
                ),
                width: 46,
                height: 46,
                child: IconButton(
                  onPressed: () => onTap(cafe),
                  icon: const Icon(Icons.location_on, color: AppColors.ink),
                ),
              ),
            ),
          ],
        ),
        const RichAttributionWidget(
          attributions: [TextSourceAttribution('OpenStreetMap contributors')],
        ),
      ],
    );
  }
}

class _CafePreviewCard extends StatelessWidget {
  const _CafePreviewCard({
    required this.cafe,
    required this.favorite,
    required this.onFavorite,
    required this.onTap,
    required this.onClose,
  });

  final Map<String, dynamic> cafe;
  final bool favorite;
  final VoidCallback onFavorite;
  final VoidCallback onTap;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) => Material(
    color: AppColors.surface,
    elevation: 7,
    shadowColor: Colors.black26,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(24),
      side: const BorderSide(color: AppColors.ink, width: 1.2),
    ),
    child: InkWell(
      borderRadius: BorderRadius.circular(24),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            _CafeThumbnail(url: cafe['thumbnail_url']?.toString(), size: 78),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    cafe['name'].toString(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    '${_distance(cafe['distance_meters'] as num)} · ${cafe['address']}',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.mutedInk,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  tooltip: favorite ? '즐겨찾기 해제' : '즐겨찾기',
                  onPressed: onFavorite,
                  style: IconButton.styleFrom(
                    backgroundColor: favorite
                        ? AppColors.lime
                        : AppColors.canvas,
                  ),
                  icon: Icon(favorite ? Icons.star : Icons.star_border),
                ),
                IconButton(
                  tooltip: '닫기',
                  onPressed: onClose,
                  icon: const Icon(Icons.close, size: 18),
                ),
              ],
            ),
          ],
        ),
      ),
    ),
  );
}

class _CafeResultList extends StatelessWidget {
  const _CafeResultList({required this.data, required this.onTap});

  final _CafeData data;
  final ValueChanged<Map<String, dynamic>> onTap;

  @override
  Widget build(BuildContext context) => ListView.separated(
    padding: const EdgeInsets.fromLTRB(16, 220, 16, 24),
    itemCount: data.items.length,
    separatorBuilder: (_, _) => const SizedBox(height: 10),
    itemBuilder: (context, index) {
      final cafe = data.items[index];
      return Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(22),
          onTap: () => onTap(cafe),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                _CafeThumbnail(
                  url: cafe['thumbnail_url']?.toString(),
                  size: 70,
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        cafe['name'].toString(),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 5),
                      Text(
                        '${_distance(cafe['distance_meters'] as num)} · ${cafe['address']}',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: AppColors.mutedInk),
                      ),
                    ],
                  ),
                ),
                Icon(
                  data.favoriteIds.contains(cafe['id'])
                      ? Icons.star
                      : Icons.arrow_forward,
                  color: data.favoriteIds.contains(cafe['id'])
                      ? AppColors.ink
                      : null,
                ),
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _CafeThumbnail extends StatelessWidget {
  const _CafeThumbnail({required this.url, required this.size});

  final String? url;
  final double size;

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(17),
    child: SizedBox.square(
      dimension: size,
      child: url == null || url!.isEmpty
          ? const ColoredBox(
              color: AppColors.canvas,
              child: Icon(Icons.local_cafe_outlined),
            )
          : Image.network(
              url!,
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => const ColoredBox(
                color: AppColors.canvas,
                child: Icon(Icons.local_cafe_outlined),
              ),
            ),
    ),
  );
}

class _CafeMessage extends StatelessWidget {
  const _CafeMessage({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: AppColors.canvas,
    child: Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 44),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    ),
  );
}

String _distance(num meters) => meters < 1000
    ? '${meters.round()}m'
    : '${(meters / 1000).toStringAsFixed(1)}km';
