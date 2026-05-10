#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

static inline unsigned char iupac4(unsigned char ch) {
    if (ch >= 'a' && ch <= 'z') {
        ch = static_cast<unsigned char>(ch - ('a' - 'A'));
    }
    switch (ch) {
        case '-': return 0x0;
        case 'A': return 0x1;
        case 'C': return 0x2;
        case 'G': return 0x3;
        case 'T': return 0x4;
        case 'R': return 0x5;
        case 'Y': return 0x6;
        case 'M': return 0x7;
        case 'K': return 0x8;
        case 'S': return 0x9;
        case 'W': return 0xA;
        case 'H': return 0xB;
        case 'B': return 0xC;
        case 'V': return 0xD;
        case 'D': return 0xE;
        case 'N': return 0xF;
        default: return 0xF;
    }
}

struct Result {
    std::uint64_t bases = 0;
    std::uint64_t encoded_bytes = 0;
    std::uint32_t checksum = 2166136261u;
};

static inline void add_packed(Result& result, unsigned char packed) {
    result.checksum ^= packed;
    result.checksum *= 16777619u;
    result.encoded_bytes += 1;
}

Result pack_fasta(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot open input file");
    }

    Result result;
    std::string line;
    int pending = -1;

    while (std::getline(input, line)) {
        if (!line.empty() && line[0] == '>') {
            continue;
        }
        for (unsigned char ch : line) {
            if (ch == '\n' || ch == '\r' || ch == ' ' || ch == '\t') {
                continue;
            }
            unsigned char nibble = iupac4(ch);
            if (pending < 0) {
                pending = nibble;
            } else {
                unsigned char packed = static_cast<unsigned char>((pending << 4) | nibble);
                add_packed(result, packed);
                pending = -1;
            }
            result.bases += 1;
        }
    }

    if (pending >= 0) {
        unsigned char packed = static_cast<unsigned char>(pending << 4);
        add_packed(result, packed);
    }

    return result;
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: io_cpp_pack_bench <input.fasta>\n";
        return 2;
    }

    auto start = std::chrono::steady_clock::now();
    Result result = pack_fasta(argv[1]);
    auto end = std::chrono::steady_clock::now();
    std::chrono::duration<double> elapsed = end - start;

    std::cout << "cpp_seconds=" << std::fixed << std::setprecision(6)
              << elapsed.count() << "\n";
    std::cout << "bases=" << result.bases << "\n";
    std::cout << "encoded_bytes=" << result.encoded_bytes << "\n";
    std::cout << "checksum=" << std::hex << std::setw(8) << std::setfill('0')
              << result.checksum << "\n";
    return 0;
}
