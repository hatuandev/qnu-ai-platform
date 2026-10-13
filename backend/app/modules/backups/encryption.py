"""Bounded-memory authenticated stream: scrypt + AES-256-GCM, mandatory EOF tag."""

import os
import struct
from typing import BinaryIO

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app.modules.backups.errors import BackupIntegrityError

MAGIC = b"QNUBKP01"
BLOCK_SIZE = 1024 * 1024
HEADER_SIZE = len(MAGIC) + 16 + 8


def cipher(password: str, header: bytes) -> AESGCM:
    if len(header) != HEADER_SIZE or not header.startswith(MAGIC):
        raise BackupIntegrityError("Định dạng sao lưu không được hỗ trợ.")
    key = Scrypt(salt=header[8:24], length=32, n=2**15, r=8, p=1).derive(password.encode("utf-8"))
    return AESGCM(key)


class EncryptedWriter:
    def __init__(self, destination: BinaryIO, password: str):
        self.destination = destination
        self.header = MAGIC + os.urandom(24)
        self.cipher = cipher(password, self.header)
        self.counter = 0
        self.buffer = bytearray()
        destination.write(self.header)

    def _frame(self, block: bytes) -> None:
        sequence = struct.pack(">I", self.counter)
        payload = self.cipher.encrypt(self.header[24:] + sequence, block, self.header + sequence)
        self.destination.write(struct.pack(">I", len(payload)))
        self.destination.write(payload)
        self.counter += 1

    def write(self, data: bytes) -> int:
        self.buffer.extend(data)
        while len(self.buffer) >= BLOCK_SIZE:
            self._frame(bytes(self.buffer[:BLOCK_SIZE]))
            del self.buffer[:BLOCK_SIZE]
        return len(data)

    def finish(self) -> None:
        if self.buffer:
            self._frame(bytes(self.buffer))
            self.buffer.clear()
        self._frame(b"")  # Detect truncation, including removal of a whole final frame.
        self.destination.flush()
        os.fsync(self.destination.fileno())


def decrypt_stream(
    source: BinaryIO, destination: BinaryIO, password: str, *, max_plain_bytes: int | None = None
) -> None:
    header = source.read(HEADER_SIZE)
    aes = cipher(password, header)
    counter = 0
    total = 0
    while True:
        length = source.read(4)
        if len(length) != 4:
            raise BackupIntegrityError("Bản sao lưu bị cắt ngắn, thiếu dấu kết thúc.")
        size = struct.unpack(">I", length)[0]
        if not 16 <= size <= BLOCK_SIZE + 16:
            raise BackupIntegrityError("Kích thước khối sao lưu không hợp lệ.")
        payload = source.read(size)
        if len(payload) != size:
            raise BackupIntegrityError("Bản sao lưu bị cắt ngắn.")
        sequence = struct.pack(">I", counter)
        block = aes.decrypt(header[24:] + sequence, payload, header + sequence)
        counter += 1
        if not block:
            if source.read(1):
                raise BackupIntegrityError("Bản sao lưu có dữ liệu thừa sau dấu kết thúc.")
            return
        total += len(block)
        if max_plain_bytes is not None and total > max_plain_bytes:
            raise BackupIntegrityError("Không đủ hạn mức dung lượng để giải mã bản sao lưu.")
        destination.write(block)
