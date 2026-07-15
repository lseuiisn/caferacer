import 'package:flutter/material.dart';

import '../../domain/cafe.dart';

class CafeCard extends StatelessWidget {
  const CafeCard({super.key, required this.cafe, required this.onTap});

  final Cafe cafe;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: cafe.thumbnailUrl != null
                    ? Image.network(
                        cafe.thumbnailUrl!,
                        width: 72,
                        height: 72,
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) =>
                            _placeholder(),
                      )
                    : _placeholder(),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      cafe.name,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      cafe.address,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: Colors.grey[600]),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        if (cafe.parkingAvailable) _tagChip('주차 가능'),
                        if (cafe.priceRange != null) _tagChip(cafe.priceRange!),
                        ...cafe.tags.take(2).map(_tagChip),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _placeholder() => Container(
    width: 72,
    height: 72,
    color: Colors.grey[300],
    child: const Icon(Icons.local_cafe, color: Colors.white),
  );

  Widget _tagChip(String label) => Padding(
    padding: const EdgeInsets.only(right: 6),
    child: Chip(
      label: Text(label, style: const TextStyle(fontSize: 11)),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      visualDensity: VisualDensity.compact,
      padding: EdgeInsets.zero,
    ),
  );
}
