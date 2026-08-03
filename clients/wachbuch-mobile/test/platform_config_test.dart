import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Android registers isolated Wachbuch connect URI schemes', () async {
    final manifest = await File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsString();
    final gradle = await File('android/app/build.gradle.kts').readAsString();
    final lint = await File('android/app/lint.xml').readAsString();

    expect(manifest, contains('android.intent.action.VIEW'));
    expect(manifest, contains('android.intent.category.BROWSABLE'));
    expect(manifest, contains('android:scheme="\${appScheme}"'));
    expect(manifest, contains('android:host="connect"'));
    expect(manifest, contains('android.permission.ACCESS_COARSE_LOCATION'));
    expect(manifest, isNot(contains('android.permission.POST_NOTIFICATIONS')));
    expect(manifest, contains('android:allowBackup="false"'));
    expect(
      manifest,
      contains('android:dataExtractionRules="@xml/data_extraction_rules"'),
    );

    expect(
      gradle,
      contains('manifestPlaceholders["appScheme"] = "wachbuch"'),
    );
    expect(
      gradle,
      contains('manifestPlaceholders["appScheme"] = "wachbuch-internal"'),
    );
    expect(gradle, contains('applicationIdSuffix = ".internal"'));
    expect(
      gradle,
      contains('manifestPlaceholders["appLabel"] = "Wachbuch Internal"'),
    );
    expect(gradle, contains('warningsAsErrors = true'));

    expect(lint, contains('NotificationPermission'));
    expect(
      lint,
      contains(
        r'com\.baseflow\.geolocator\.location\.BackgroundNotification',
      ),
    );
  });

  test('iOS registers the wachbuch URI scheme', () async {
    final plist = await File('ios/Runner/Info.plist').readAsString();

    expect(plist, contains('<key>CFBundleURLTypes</key>'));
    expect(plist, contains('<string>wachbuch</string>'));
    expect(plist, contains('<key>NSLocationWhenInUseUsageDescription</key>'));
    expect(plist, contains('Sonnenaufgang und Sonnenuntergang'));
    expect(plist, contains('<key>ITSAppUsesNonExemptEncryption</key>'));
  });
}
