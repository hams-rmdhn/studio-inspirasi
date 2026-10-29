// SPDX-License-Identifier: AGPL-3.0-or-later
// Compatibility shim for macOS Monterey 12.x (x86_64):
// 1. C++17 floating-point std::__1::to_chars (added to macOS system libc++ in 13.3)
// 2. Accelerate ILP64 cblas_sgemm$NEWLAPACK$ILP64 (added in macOS 13.3)
// 3. VideoToolbox VTPixelRotationSession* symbols (added in macOS 13.0)

#include <charconv>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <system_error>
#include <CoreFoundation/CoreFoundation.h>
#include <Accelerate/Accelerate.h>

namespace std {
inline namespace __1 {

namespace {

template <typename T>
to_chars_result format_float_impl(char* first, char* last, T value, const char* fmt, int precision, bool has_precision) noexcept {
    if (first > last) {
        return {last, errc::value_too_large};
    }
    if (std::isnan(value)) {
        const char* s = std::signbit(value) ? "-nan" : "nan";
        size_t len = std::strlen(s);
        if (static_cast<size_t>(last - first) < len) {
            return {last, errc::value_too_large};
        }
        std::memcpy(first, s, len);
        return {first + len, errc{}};
    }
    if (std::isinf(value)) {
        const char* s = std::signbit(value) ? "-inf" : "inf";
        size_t len = std::strlen(s);
        if (static_cast<size_t>(last - first) < len) {
            return {last, errc::value_too_large};
        }
        std::memcpy(first, s, len);
        return {first + len, errc{}};
    }

    char buf[512];
    int written = 0;
    if (has_precision) {
        written = std::snprintf(buf, sizeof(buf), fmt, precision, value);
    } else {
        written = std::snprintf(buf, sizeof(buf), fmt, value);
    }
    if (written < 0 || static_cast<size_t>(written) >= sizeof(buf)) {
        return {last, errc::value_too_large};
    }
    // Strip leading "0x" or "-0x" if hex format was requested (std::to_chars hex has no 0x prefix)
    const char* src = buf;
    char cleaned[512];
    if (std::strstr(fmt, "a") != nullptr) {
        char* dst = cleaned;
        if (*src == '-') {
            *dst++ = *src++;
        }
        if (src[0] == '0' && (src[1] == 'x' || src[1] == 'X')) {
            src += 2;
        }
        std::strcpy(dst, src);
        src = cleaned;
        written = static_cast<int>(std::strlen(src));
    }

    if (last - first < written) {
        return {last, errc::value_too_large};
    }
    std::memcpy(first, src, static_cast<size_t>(written));
    return {first + written, errc{}};
}

} // namespace

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, float value) noexcept {
    return format_float_impl(first, last, static_cast<double>(value), "%.9g", 0, false);
}

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, double value) noexcept {
    return format_float_impl(first, last, value, "%.17g", 0, false);
}

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, long double value) noexcept {
    return format_float_impl(first, last, value, "%.21Lg", 0, false);
}

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, float value, chars_format fmt) noexcept {
    const char* spec = "%.9g";
    if (fmt == chars_format::scientific) spec = "%.6e";
    else if (fmt == chars_format::fixed) spec = "%.6f";
    else if (fmt == chars_format::hex) spec = "%a";
    return format_float_impl(first, last, static_cast<double>(value), spec, 0, false);
}

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, double value, chars_format fmt) noexcept {
    const char* spec = "%.17g";
    if (fmt == chars_format::scientific) spec = "%.6e";
    else if (fmt == chars_format::fixed) spec = "%.6f";
    else if (fmt == chars_format::hex) spec = "%a";
    return format_float_impl(first, last, value, spec, 0, false);
}

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, long double value, chars_format fmt) noexcept {
    const char* spec = "%.21Lg";
    if (fmt == chars_format::scientific) spec = "%.6Le";
    else if (fmt == chars_format::fixed) spec = "%.6Lf";
    else if (fmt == chars_format::hex) spec = "%La";
    return format_float_impl(first, last, value, spec, 0, false);
}

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, float value, chars_format fmt, int precision) noexcept {
    const char* spec = "%.*g";
    if (fmt == chars_format::scientific) spec = "%.*e";
    else if (fmt == chars_format::fixed) spec = "%.*f";
    else if (fmt == chars_format::hex) spec = "%.*a";
    return format_float_impl(first, last, static_cast<double>(value), spec, precision, true);
}

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, double value, chars_format fmt, int precision) noexcept {
    const char* spec = "%.*g";
    if (fmt == chars_format::scientific) spec = "%.*e";
    else if (fmt == chars_format::fixed) spec = "%.*f";
    else if (fmt == chars_format::hex) spec = "%.*a";
    return format_float_impl(first, last, value, spec, precision, true);
}

__attribute__((visibility("default")))
to_chars_result to_chars(char* first, char* last, long double value, chars_format fmt, int precision) noexcept {
    const char* spec = "%.*Lg";
    if (fmt == chars_format::scientific) spec = "%.*Le";
    else if (fmt == chars_format::fixed) spec = "%.*Lf";
    else if (fmt == chars_format::hex) spec = "%.*La";
    return format_float_impl(first, last, value, spec, precision, true);
}

} // namespace __1
} // namespace std

// Accelerate ILP64 compatibility bridge for macOS 12
extern "C" __attribute__((visibility("default")))
void cblas_sgemm_ilp64(
    enum CBLAS_ORDER Order,
    enum CBLAS_TRANSPOSE TransA,
    enum CBLAS_TRANSPOSE TransB,
    long M,
    long N,
    long K,
    float alpha,
    const float *A,
    long lda,
    const float *B,
    long ldb,
    float beta,
    float *C,
    long ldc
) __asm__("_cblas_sgemm$NEWLAPACK$ILP64");

extern "C" void cblas_sgemm_ilp64(
    enum CBLAS_ORDER Order,
    enum CBLAS_TRANSPOSE TransA,
    enum CBLAS_TRANSPOSE TransB,
    long M,
    long N,
    long K,
    float alpha,
    const float *A,
    long lda,
    const float *B,
    long ldb,
    float beta,
    float *C,
    long ldc
) {
    cblas_sgemm(
        Order, TransA, TransB,
        static_cast<int>(M), static_cast<int>(N), static_cast<int>(K),
        alpha, A, static_cast<int>(lda),
        B, static_cast<int>(ldb),
        beta, C, static_cast<int>(ldc)
    );
}

// VideoToolbox VTPixelRotationSession compatibility stubs for macOS 12 (added in macOS 13.0)
extern "C" {

typedef void* VTPixelRotationSessionRef;

__attribute__((visibility("default")))
extern const CFStringRef kVTPixelRotationPropertyKey_Rotation = CFSTR("Rotation");
__attribute__((visibility("default")))
extern const CFStringRef kVTPixelRotationPropertyKey_FlipHorizontalOrientation = CFSTR("FlipHorizontalOrientation");
__attribute__((visibility("default")))
extern const CFStringRef kVTPixelRotationPropertyKey_FlipVerticalOrientation = CFSTR("FlipVerticalOrientation");

__attribute__((visibility("default")))
extern const CFStringRef kVTRotation_0 = CFSTR("0");
__attribute__((visibility("default")))
extern const CFStringRef kVTRotation_CW90 = CFSTR("CW90");
__attribute__((visibility("default")))
extern const CFStringRef kVTRotation_180 = CFSTR("180");
__attribute__((visibility("default")))
extern const CFStringRef kVTRotation_CCW90 = CFSTR("CCW90");

__attribute__((visibility("default")))
OSStatus VTPixelRotationSessionCreate(CFAllocatorRef allocator, VTPixelRotationSessionRef* rotationSessionOut) {
    (void)allocator;
    if (rotationSessionOut) {
        *rotationSessionOut = nullptr;
    }
    return -12900; // kVTPropertyNotSupportedErr
}

__attribute__((visibility("default")))
void VTPixelRotationSessionInvalidate(VTPixelRotationSessionRef session) {
    (void)session;
}

__attribute__((visibility("default")))
OSStatus VTPixelRotationSessionRotateImage(
    VTPixelRotationSessionRef session,
    CVPixelBufferRef sourceBuffer,
    CVPixelBufferRef destinationBuffer
) {
    (void)session;
    (void)sourceBuffer;
    (void)destinationBuffer;
    return -12900;
}

} // extern "C"
