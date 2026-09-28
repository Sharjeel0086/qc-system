package com.example.qcsystem.auth

import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

object AuthManager {
    private const val ITERATIONS = 200_000
    private const val KEY_LENGTH = 256

    fun hashPassword(password: String, existingSalt: String? = null): Pair<String, String> {
        val saltBytes = if (existingSalt != null) {
            hexToBytes(existingSalt)
        } else {
            val random = SecureRandom()
            val salt = ByteArray(16)
            random.nextBytes(salt)
            salt
        }

        val spec = PBEKeySpec(password.toCharArray(), saltBytes, ITERATIONS, KEY_LENGTH)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val hash = factory.generateSecret(spec).encoded

        return bytesToHex(hash) to bytesToHex(saltBytes)
    }

    fun verifyPassword(password: String, storedHash: String, salt: String): Boolean {
        val (calcHash, _) = hashPassword(password, salt)
        return MessageDigest.isEqual(hexToBytes(calcHash), hexToBytes(storedHash))
    }

    private fun bytesToHex(bytes: ByteArray): String {
        val sb = StringBuilder()
        for (b in bytes) {
            sb.append(String.format("%02x", b))
        }
        return sb.toString()
    }

    private fun hexToBytes(hex: String): ByteArray {
        val len = hex.length
        val data = ByteArray(len / 2)
        var i = 0
        while (i < len) {
            data[i / 2] = ((Character.digit(hex[i], 16) shl 4) + Character.digit(hex[i + 1], 16)).toByte()
            i += 2
        }
        return data
    }
}
