import 'package:flutter/material.dart';

import '../../domain/social_login_type.dart';

class SocialLoginButton extends StatelessWidget {
  const SocialLoginButton({
    super.key,
    required this.type,
    required this.isLoading,
    required this.onPressed,
  });

  final SocialLoginType type;
  final bool isLoading;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final isKakao = type == SocialLoginType.kakao;
    final label = isKakao ? '카카오로 시작하기' : '구글로 시작하기';
    final bgColor = isKakao ? const Color(0xFFFEE500) : Colors.white;
    final fgColor = isKakao ? Colors.black87 : Colors.black87;

    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: bgColor,
          foregroundColor: fgColor,
          side: isKakao ? null : const BorderSide(color: Color(0xFFDDDDDD)),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        child: isLoading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Text(label),
      ),
    );
  }
}
