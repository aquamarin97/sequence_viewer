#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

struct Result {
    std::uint64_t bases = 0;
    std::uint64_t encoded_bytes = 0;
    std::uint32_t checksum = 2166136261u;
};

// Lookup table (en hızlı yöntem)
static unsigned char IUPAC4[256];

void init_iupac_table() {
    for (int i = 0; i < 256; ++i) {
        IUPAC4[i] = 0xF;  // default
    }
    IUPAC4['-'] = 0x0;
    IUPAC4['A'] = IUPAC4['a'] = 0x1;
    IUPAC4['C'] = IUPAC4['c'] = 0x2;
    IUPAC4['G'] = IUPAC4['g'] = 0x3;
    IUPAC4['T'] = IUPAC4['t'] = 0x4;
    IUPAC4['R'] = IUPAC4['r'] = 0x5;
    IUPAC4['Y'] = IUPAC4['y'] = 0x6;
    IUPAC4['M'] = IUPAC4['m'] = 0x7;
    IUPAC4['K'] = IUPAC4['k'] = 0x8;
    IUPAC4['S'] = IUPAC4['s'] = 0x9;
    IUPAC4['W'] = IUPAC4['w'] = 0xA;
    IUPAC4['H'] = IUPAC4['h'] = 0xB;
    IUPAC4['B'] = IUPAC4['b'] = 0xC;
    IUPAC4['V'] = IUPAC4['v'] = 0xD;
    IUPAC4['D'] = IUPAC4['d'] = 0xE;
    IUPAC4['N'] = IUPAC4['n'] = 0xF;
}

inline void add_packed(Result& r, unsigned char packed) {
    r.checksum ^= packed;
    r.checksum *= 16777619u;
    r.encoded_bytes++;
}

Result pack_fasta(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("cannot open input file");
    }

    // Büyük buffer + performans ayarları
    constexpr std::size_t BUFFER_SIZE = 256 * 1024;  // 256 KB
    char buffer[BUFFER_SIZE];
    file.rdbuf()->pubsetbuf(buffer, sizeof(buffer));

    Result result;
    int pending = -1;
    bool in_header = false;

    while (true) {
        file.read(buffer, BUFFER_SIZE);
        std::size_t bytes_read = file.gcount();
        if (bytes_read == 0) break;

        for (std::size_t i = 0; i < bytes_read; ++i) {
            unsigned char ch = static_cast<unsigned char>(buffer[i]);

            if (in_header) {
                if (ch == '\n') in_header = false;
                continue;
            }
            if (ch == '>') {
                in_header = true;
                continue;
            }
            if (ch == '\n' || ch == '\r' || ch == ' ' || ch == '\t') {
                continue;
            }

            unsigned char nibble = IUPAC4[ch];

            if (pending < 0) {
                pending = nibble;
            } else {
                unsigned char packed = static_cast<unsigned char>((pending << 4) | nibble);
                add_packed(result, packed);
                pending = -1;
            }
            result.bases++;
        }
    }

    // Son kalan nibble
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

    init_iupac_table();   // Bir kere çağır

    auto start = std::chrono::steady_clock::now();
    Result result = pack_fasta(argv[1]);
    auto end = std::chrono::steady_clock::now();

    std::chrono::duration<double> elapsed = end - start;

    std::cout << "cpp_seconds=" << std::fixed << std::setprecision(6) << elapsed.count() << "\n";
    std::cout << "bases=" << result.bases << "\n";
    std::cout << "encoded_bytes=" << result.encoded_bytes << "\n";
    std::cout << "checksum=" << std::hex << std::setw(8) << std::setfill('0')
              << result.checksum << "\n";

    return 0;
}