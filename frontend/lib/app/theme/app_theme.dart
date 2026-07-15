import 'package:flutter/material.dart';

class AppTheme {
  AppTheme._();

  static final light = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF315C46)),
    scaffoldBackgroundColor: const Color(0xFFF7F8F6),
    navigationBarTheme: const NavigationBarThemeData(height: 72),
  );
}
