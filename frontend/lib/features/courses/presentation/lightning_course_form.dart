import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/widgets/tmap_native_map.dart';
import '../../auth/providers.dart';
import '../../drive_tracking/providers.dart';

enum _TargetPoint { start, destination }

class _Place {
  const _Place(this.name, this.latitude, this.longitude, [this.address]);

  final String name;
  final double latitude;
  final double longitude;
  final String? address;
}

class LightningCourseForm extends ConsumerStatefulWidget {
  const LightningCourseForm({this.crewId, super.key});

  final int? crewId;

  @override
  ConsumerState<LightningCourseForm> createState() => _LightningCourseFormState();
}

class _LightningCourseFormState extends ConsumerState<LightningCourseForm> {
  final _name = TextEditingController();
  final _search = TextEditingController();
  final _baselineMinutes = TextEditingController();
  DateTime _eventDate = DateTime.now();
  _TargetPoint _target = _TargetPoint.start;
  _Place? _start;
  _Place? _destination;
  List<_Place> _results = [];
  String _rankingMode = 'fastest';
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _search.dispose();
    _baselineMinutes.dispose();
    super.dispose();
  }

  void _assign(_Place place) {
    setState(() {
      if (_target == _TargetPoint.start) {
        _start = place;
        _target = _TargetPoint.destination;
      } else {
        _destination = place;
      }
      _results = [];
    });
  }

  Future<void> _searchPlaces() async {
    if (_search.text.trim().length < 2) return;
    setState(() => _busy = true);
    try {
      final raw = await ref.read(apiClientProvider).get('/places/search', query: {
        'q': _search.text.trim(),
      }) as List<dynamic>;
      setState(() => _results = raw.map((item) {
        final json = item as Map<String, dynamic>;
        final point = json['coordinate'] as Map<String, dynamic>;
        return _Place(
          json['name'].toString(),
          (point['latitude'] as num).toDouble(),
          (point['longitude'] as num).toDouble(),
          json['address']?.toString(),
        );
      }).toList());
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _useCurrentLocation() async {
    try {
      final position = await ref.read(driveTrackingServiceProvider).currentPosition();
      _assign(_Place('현재 위치', position.latitude, position.longitude));
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    }
  }

  Future<void> _submit() async {
    if (_name.text.trim().length < 2 || _start == null || _destination == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('이름, 출발지, 목적지를 모두 입력해 주세요.')),
      );
      return;
    }
    final baselineMinutes = int.tryParse(_baselineMinutes.text.trim());
    if (baselineMinutes == null || baselineMinutes <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('기준 시간(분)을 입력해 주세요.')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final body = {
        'name': _name.text.trim(),
        'event_date': _eventDate.toIso8601String().substring(0, 10),
        'start_name': _start!.name,
        'start': {'latitude': _start!.latitude, 'longitude': _start!.longitude},
        'destination_name': _destination!.name,
        'destination': {
          'latitude': _destination!.latitude,
          'longitude': _destination!.longitude,
        },
        'ranking_mode': _rankingMode,
        'baseline_duration_seconds': baselineMinutes * 60,
      };
      final endpoint = widget.crewId == null
          ? '/lightning-courses'
          : '/crews/${widget.crewId}/courses';
      await ref.read(apiClientProvider).post(endpoint, body: body);
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final markers = [
      if (_start != null)
        TmapNativeMarker(
          id: 'start', latitude: _start!.latitude, longitude: _start!.longitude,
          title: _start!.name, color: 'start',
        ),
      if (_destination != null)
        TmapNativeMarker(
          id: 'destination', latitude: _destination!.latitude,
          longitude: _destination!.longitude, title: _destination!.name,
          color: 'destination',
        ),
    ];
    return Scaffold(
      appBar: AppBar(title: Text(
        widget.crewId == null ? '공개 번개코스 만들기' : '크루 번개코스 만들기',
      )),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(controller: _name, decoration: const InputDecoration(labelText: '번개코스 이름')),
          const SizedBox(height: 16),
          SegmentedButton<_TargetPoint>(
            segments: const [
              ButtonSegment(value: _TargetPoint.start, label: Text('출발지')),
              ButtonSegment(value: _TargetPoint.destination, label: Text('목적지')),
            ],
            selected: {_target},
            onSelectionChanged: (value) => setState(() => _target = value.first),
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: TextField(
              controller: _search,
              decoration: const InputDecoration(labelText: '장소 검색'),
              onSubmitted: (_) => _searchPlaces(),
            )),
            IconButton(onPressed: _busy ? null : _searchPlaces, icon: const Icon(Icons.search)),
            IconButton(onPressed: _useCurrentLocation, tooltip: '현재 위치', icon: const Icon(Icons.my_location)),
          ]),
          ..._results.map((place) => ListTile(
            title: Text(place.name),
            subtitle: Text(place.address ?? ''),
            onTap: () => _assign(place),
          )),
          if (Platform.isAndroid)
            SizedBox(
              height: 260,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: TmapNativeMap(
                  centerLatitude: _start?.latitude ?? 37.5665,
                  centerLongitude: _start?.longitude ?? 126.9780,
                  markers: markers,
                  onMapTap: (lat, lon) => _assign(_Place(
                    _target == _TargetPoint.start ? '지도 출발지' : '지도 목적지', lat, lon,
                  )),
                ),
              ),
            ),
          const SizedBox(height: 8),
          Text('출발: ${_start?.name ?? '미선택'}'),
          Text('도착: ${_destination?.name ?? '미선택'}'),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('진행 날짜'),
            subtitle: Text(_eventDate.toIso8601String().substring(0, 10)),
            trailing: const Icon(Icons.calendar_today),
            onTap: () async {
              final selected = await showDatePicker(
                context: context,
                initialDate: _eventDate,
                firstDate: DateTime.now(),
                lastDate: DateTime.now().add(const Duration(days: 30)),
              );
              if (selected != null) setState(() => _eventDate = selected);
            },
          ),
          DropdownButtonFormField<String>(
            initialValue: _rankingMode,
            decoration: const InputDecoration(labelText: '랭킹 방식'),
            items: const [
              DropdownMenuItem(value: 'fastest', child: Text('주행 시간이 짧은 순')),
              DropdownMenuItem(value: 'closest_to_baseline', child: Text('기준 시간에 가까운 순')),
            ],
            onChanged: (value) => setState(() => _rankingMode = value!),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _baselineMinutes,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: '기준 시간(분)',
              helperText: '±% 표시의 기준이며, 랭킹 방식과 별도로 사용됩니다.',
            ),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: Text(widget.crewId == null ? '번개코스 공개' : '크루에 등록'),
          ),
        ],
      ),
    );
  }
}
