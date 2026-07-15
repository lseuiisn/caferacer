class Cafe {
  final int id;
  final String name;
  final String address;
  final double latitude;
  final double longitude;
  final String? priceRange;
  final bool parkingAvailable;
  final List<String> tags;
  final String? thumbnailUrl;

  const Cafe({
    required this.id,
    required this.name,
    required this.address,
    required this.latitude,
    required this.longitude,
    this.priceRange,
    required this.parkingAvailable,
    this.tags = const [],
    this.thumbnailUrl,
  });

  factory Cafe.fromJson(Map<String, dynamic> json) => Cafe(
    id: json['id'] as int,
    name: json['name'] as String,
    address: json['address'] as String,
    latitude: (json['latitude'] as num).toDouble(),
    longitude: (json['longitude'] as num).toDouble(),
    priceRange: json['price_range'] as String?,
    parkingAvailable: json['parking_available'] as bool? ?? false,
    tags: (json['tags'] as List<dynamic>? ?? [])
        .map((e) => e as String)
        .toList(),
    thumbnailUrl: json['thumbnail_url'] as String?,
  );
}
