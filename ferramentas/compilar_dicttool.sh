#!/bin/sh
# Compila dicttool (a ferramenta de AOSP que converte gl_wordlist.combined no .dict
# binario dos teclados AOSP/HeliBoard) desde o código oficial de Android (LatinIME,
# Apache 2.0) e déixao en fontes/cache/dicttool_aosp.jar, onde o colle construir.py.
#
#     sh ferramentas/compilar_dicttool.sh
#
# Precisa git e un JDK 11 ou posterior (javac); o .jar resultante funciona con Java 8.
set -eu
RAIZ=$(cd "$(dirname "$0")/.." && pwd)
CACHE="$RAIZ/fontes/cache"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$CACHE"

git clone -q --depth 1 -b android11-release \
    https://android.googlesource.com/platform/packages/inputmethods/LatinIME "$TMP/LatinIME"
L="$TMP/LatinIME"
S="$TMP/stubs"

# Substitutos: anotacións jsr305 e o comando «test» (as autoprobas precisan JUnit).
mkdir -p "$S/javax/annotation" "$S/com/android/inputmethod/latin/dicttool"
for a in Nonnull Nullable; do
    printf 'package javax.annotation;\nimport java.lang.annotation.*;\n@Retention(RetentionPolicy.CLASS)\npublic @interface %s {}\n' "$a" \
        > "$S/javax/annotation/$a.java"
done
cat > "$S/com/android/inputmethod/latin/dicttool/Test.java" <<'EOF'
package com.android.inputmethod.latin.dicttool;
public class Test extends Dicttool.Command {
    public String getHelp() { return "test (autoprobas non compiladas)"; }
    public void run() { System.out.println("Autoprobas non compiladas."); }
}
EOF

# As mesmas fontes que tools/dicttool/Android.bp (dicttool_deps), sen as de JUnit.
J="$L/java/src/com/android/inputmethod/latin"
{
    find "$L/tools/dicttool/src" "$L/tools/dicttool/compat" "$L/common/src" "$J/makedict" \
         "$L/tests/src/com/android/inputmethod/latin/makedict" "$S" -name '*.java'
    for f in BinaryDictionary DicTraverseSession Dictionary NgramContext SuggestedWords \
             settings/SettingsValuesForSuggestion utils/BinaryDictionaryUtils utils/CombinedFormatUtils \
             utils/JniUtils define/DebugFlags define/DecoderSpecificConstants; do
        echo "$J/$f.java"
    done
    echo "$L/tests/src/com/android/inputmethod/latin/utils/ByteArrayDictBuffer.java"
} | xargs grep -L -E 'import (junit|android\.test|org\.junit)' \
  | grep -v '/tools/dicttool/src/com/android/inputmethod/latin/dicttool/Test.java$' > "$TMP/fontes.txt"

mkdir "$TMP/build"
javac -nowarn --release 8 -encoding UTF-8 -d "$TMP/build" @"$TMP/fontes.txt"
printf 'Main-Class: com.android.inputmethod.latin.dicttool.Dicttool\n' > "$TMP/manifest.txt"
jar cfm "$CACHE/dicttool_aosp.jar" "$TMP/manifest.txt" -C "$TMP/build" .
echo "$CACHE/dicttool_aosp.jar"
