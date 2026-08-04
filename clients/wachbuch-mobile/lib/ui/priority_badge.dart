import 'package:flutter/material.dart';

import '../theme/design_tokens.dart';

class PriorityBadge extends StatelessWidget {
  const PriorityBadge({
    super.key,
    required this.priority,
    this.compact = false,
    this.label,
  });

  final String priority;
  final bool compact;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final color = WachbuchTokens.priorityColor(priority);
    final text = label ?? _defaultLabel(priority);

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? WachbuchTokens.spaceSm : WachbuchTokens.spaceMd,
        vertical: compact ? WachbuchTokens.spaceXs : 6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        border: Border.all(color: color.withValues(alpha: 0.5), width: 1),
        borderRadius: BorderRadius.circular(WachbuchTokens.radiusSm),
      ),
      constraints: BoxConstraints(minHeight: compact ? 28 : 36),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: compact ? 6 : 8,
            height: compact ? 6 : 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          SizedBox(width: compact ? WachbuchTokens.spaceXs : WachbuchTokens.spaceSm),
          Text(
            text,
            style: TextStyle(
              color: color,
              fontSize: compact ? WachbuchTokens.textCaption : WachbuchTokens.textBody,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  String _defaultLabel(String p) {
    return switch (p) {
      'urgent' || 'high' => 'Dringend',
      'important' || 'medium' => 'Wichtig',
      'done' || 'low' => 'Erledigt',
      _ => 'Normal',
    };
  }
}
