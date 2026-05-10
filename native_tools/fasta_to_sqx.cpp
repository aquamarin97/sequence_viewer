#include <array>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::uint8_t MAGIC[8] = {'S', 'Q', 'X', 0x00, 0x01, 0x00, 0x00, 0x00};
constexpr std::uint16_t FORMAT_VERSION = 1;
constexpr const char* APP_VERSION = "0.1.0";
constexpr std::uint32_t BLOCK_PROJECT_META = 0x00000001;
constexpr std::uint32_t BLOCK_SEQUENCES = 0x00000002;
constexpr std::uint32_t BLOCK_DIR_ENTRY_SIZE = 22;
constexpr std::uint8_t SEQ_TYPE_NUCLEOTIDE = 0x01;
constexpr std::uint8_t ENCODING_IUPAC4 = 0x01;

struct RecordInfo {
    std::array<std::uint8_t, 16> uuid{};
    std::string header;
    std::uint64_t base_count = 0;
    std::uint64_t encoded_len = 0;
    std::uint64_t data_offset = 0;
};

void write_u8(std::ostream& out, std::uint8_t value) {
    out.put(static_cast<char>(value));
}

void write_u16(std::ostream& out, std::uint16_t value) {
    write_u8(out, static_cast<std::uint8_t>(value & 0xFF));
    write_u8(out, static_cast<std::uint8_t>((value >> 8) & 0xFF));
}

void write_u32(std::ostream& out, std::uint32_t value) {
    for (int shift = 0; shift < 32; shift += 8) {
        write_u8(out, static_cast<std::uint8_t>((value >> shift) & 0xFF));
    }
}

void write_u64(std::ostream& out, std::uint64_t value) {
    for (int shift = 0; shift < 64; shift += 8) {
        write_u8(out, static_cast<std::uint8_t>((value >> shift) & 0xFF));
    }
}

void write_i64(std::ostream& out, std::int64_t value) {
    write_u64(out, static_cast<std::uint64_t>(value));
}

std::string strip_cr(std::string line) {
    if (!line.empty() && line.back() == '\r') {
        line.pop_back();
    }
    return line;
}

std::string trim_ascii(const std::string& text) {
    std::size_t first = 0;
    while (first < text.size() && (text[first] == ' ' || text[first] == '\t')) {
        ++first;
    }
    std::size_t last = text.size();
    while (last > first && (text[last - 1] == ' ' || text[last - 1] == '\t')) {
        --last;
    }
    return text.substr(first, last - first);
}

std::string basename_of(const std::string& path) {
    std::size_t pos = path.find_last_of("/\\");
    return pos == std::string::npos ? path : path.substr(pos + 1);
}

std::string stem_of(const std::string& path) {
    std::string name = basename_of(path);
    std::size_t dot = name.find_last_of('.');
    return dot == std::string::npos ? name : name.substr(0, dot);
}

std::array<std::uint8_t, 16> make_uuid(std::uint64_t index) {
    static std::mt19937_64 rng(
        static_cast<std::uint64_t>(
            std::chrono::high_resolution_clock::now().time_since_epoch().count()));
    std::array<std::uint8_t, 16> bytes{};
    std::uint64_t a = rng() ^ index;
    std::uint64_t b = rng() ^ (index << 1);
    for (int i = 0; i < 8; ++i) {
        bytes[i] = static_cast<std::uint8_t>((a >> (i * 8)) & 0xFF);
        bytes[8 + i] = static_cast<std::uint8_t>((b >> (i * 8)) & 0xFF);
    }
    bytes[6] = static_cast<std::uint8_t>((bytes[6] & 0x0F) | 0x40);
    bytes[8] = static_cast<std::uint8_t>((bytes[8] & 0x3F) | 0x80);
    return bytes;
}

bool is_base_byte(unsigned char ch) {
    return !(ch == '\n' || ch == '\r' || ch == ' ' || ch == '\t');
}

std::uint8_t iupac4(unsigned char ch) {
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

void require_u16_size(const std::string& value, const char* field_name) {
    if (value.size() > 65535) {
        throw std::runtime_error(std::string(field_name) + " is longer than SQX allows");
    }
}

std::uint64_t record_meta_len(const std::string& header, const std::string& source_file) {
    require_u16_size(header, "header");
    require_u16_size(source_file, "source_file");
    return 2 + header.size() + 2 + source_file.size() + 2 + 4;
}

std::vector<RecordInfo> scan_fasta(const std::string& input_path,
                                   const std::string& source_file,
                                   std::uint64_t& sequence_block_len,
                                   std::uint64_t& total_bases) {
    std::ifstream input(input_path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot open FASTA input");
    }

    std::vector<RecordInfo> records;
    std::string line;
    std::int64_t current = -1;

    while (std::getline(input, line)) {
        line = strip_cr(std::move(line));
        if (!line.empty() && line[0] == '>') {
            RecordInfo info;
            info.uuid = make_uuid(records.size());
            info.header = trim_ascii(line.substr(1));
            require_u16_size(info.header, "header");
            records.push_back(std::move(info));
            current = static_cast<std::int64_t>(records.size()) - 1;
            continue;
        }
        if (current < 0 || line.empty()) {
            continue;
        }
        for (unsigned char ch : line) {
            if (is_base_byte(ch)) {
                records[static_cast<std::size_t>(current)].base_count += 1;
                total_bases += 1;
            }
        }
    }

    if (records.empty()) {
        throw std::runtime_error("no FASTA records found");
    }

    std::uint64_t current_offset = 4 + static_cast<std::uint64_t>(records.size()) * 40;
    for (RecordInfo& rec : records) {
        rec.encoded_len = (rec.base_count + 1) / 2;
        rec.data_offset = current_offset + record_meta_len(rec.header, source_file);
        current_offset += record_meta_len(rec.header, source_file) + rec.encoded_len;
    }
    sequence_block_len = current_offset;
    return records;
}

std::vector<std::uint8_t> build_project_meta(const std::string& project_name) {
    require_u16_size(project_name, "project_name");
    std::vector<std::uint8_t> data;
    std::int64_t now = static_cast<std::int64_t>(std::time(nullptr));

    auto push_u8 = [&data](std::uint8_t value) { data.push_back(value); };
    auto push_u16 = [&push_u8](std::uint16_t value) {
        push_u8(static_cast<std::uint8_t>(value & 0xFF));
        push_u8(static_cast<std::uint8_t>((value >> 8) & 0xFF));
    };
    auto push_u64 = [&push_u8](std::uint64_t value) {
        for (int shift = 0; shift < 64; shift += 8) {
            push_u8(static_cast<std::uint8_t>((value >> shift) & 0xFF));
        }
    };

    push_u64(static_cast<std::uint64_t>(now));
    push_u64(static_cast<std::uint64_t>(now));
    std::string app_version = APP_VERSION;
    push_u16(static_cast<std::uint16_t>(app_version.size()));
    data.insert(data.end(), app_version.begin(), app_version.end());
    push_u16(static_cast<std::uint16_t>(project_name.size()));
    data.insert(data.end(), project_name.begin(), project_name.end());
    return data;
}

void write_record_meta(std::ostream& out,
                       const std::string& header,
                       const std::string& source_file) {
    write_u16(out, static_cast<std::uint16_t>(header.size()));
    out.write(header.data(), static_cast<std::streamsize>(header.size()));
    write_u16(out, static_cast<std::uint16_t>(source_file.size()));
    out.write(source_file.data(), static_cast<std::streamsize>(source_file.size()));
    write_u8(out, SEQ_TYPE_NUCLEOTIDE);
    write_u8(out, ENCODING_IUPAC4);
    write_u32(out, 0);  // annotation count
}

void finish_record_byte(std::ostream& out,
                        int& pending,
                        std::uint64_t& written,
                        const RecordInfo& rec) {
    if (pending >= 0) {
        write_u8(out, static_cast<std::uint8_t>(pending << 4));
        pending = -1;
        written += 1;
    }
    if (written != rec.encoded_len) {
        throw std::runtime_error("encoded length mismatch while writing SQX");
    }
}

void write_sequences_block(std::ostream& out,
                           const std::string& input_path,
                           const std::string& source_file,
                           const std::vector<RecordInfo>& records) {
    write_u32(out, static_cast<std::uint32_t>(records.size()));
    for (const RecordInfo& rec : records) {
        out.write(reinterpret_cast<const char*>(rec.uuid.data()), 16);
        write_u64(out, rec.data_offset);
        write_u64(out, rec.encoded_len);
        write_u64(out, rec.base_count);
    }

    std::ifstream input(input_path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot reopen FASTA input");
    }

    std::string line;
    std::size_t index = 0;
    bool in_record = false;
    int pending = -1;
    std::uint64_t written_for_record = 0;

    while (std::getline(input, line)) {
        line = strip_cr(std::move(line));
        if (!line.empty() && line[0] == '>') {
            if (in_record) {
                finish_record_byte(out, pending, written_for_record, records[index]);
                index += 1;
                written_for_record = 0;
            }
            if (index >= records.size()) {
                throw std::runtime_error("record count changed between FASTA passes");
            }
            std::string header = trim_ascii(line.substr(1));
            if (header != records[index].header) {
                throw std::runtime_error("record order changed between FASTA passes");
            }
            write_record_meta(out, records[index].header, source_file);
            in_record = true;
            pending = -1;
            continue;
        }
        if (!in_record || line.empty()) {
            continue;
        }
        for (unsigned char ch : line) {
            if (!is_base_byte(ch)) {
                continue;
            }
            std::uint8_t nibble = iupac4(ch);
            if (pending < 0) {
                pending = nibble;
            } else {
                write_u8(out, static_cast<std::uint8_t>((pending << 4) | nibble));
                pending = -1;
                written_for_record += 1;
            }
        }
    }

    if (in_record) {
        finish_record_byte(out, pending, written_for_record, records[index]);
        index += 1;
    }
    if (index != records.size()) {
        throw std::runtime_error("record count mismatch after writing SQX");
    }
}

void write_sqx(const std::string& input_path,
               const std::string& output_path,
               const std::string& project_name) {
    std::string source_file = basename_of(input_path);
    std::uint64_t sequence_block_len = 0;
    std::uint64_t total_bases = 0;
    std::vector<RecordInfo> records =
        scan_fasta(input_path, source_file, sequence_block_len, total_bases);
    std::vector<std::uint8_t> project_meta = build_project_meta(project_name);

    const std::string app_version = APP_VERSION;
    const std::uint32_t block_count = 2;
    const std::uint64_t header_len =
        8 + 2 + 2 + app_version.size() + 4 + block_count * BLOCK_DIR_ENTRY_SIZE;
    const std::uint64_t project_meta_offset = header_len;
    const std::uint64_t sequences_offset = project_meta_offset + project_meta.size();

    std::ofstream out(output_path, std::ios::binary);
    if (!out) {
        throw std::runtime_error("cannot open SQX output");
    }

    out.write(reinterpret_cast<const char*>(MAGIC), 8);
    write_u16(out, FORMAT_VERSION);
    write_u16(out, static_cast<std::uint16_t>(app_version.size()));
    out.write(app_version.data(), static_cast<std::streamsize>(app_version.size()));
    write_u32(out, block_count);

    write_u32(out, BLOCK_PROJECT_META);
    write_u64(out, project_meta_offset);
    write_u64(out, project_meta.size());
    write_u16(out, 1);

    write_u32(out, BLOCK_SEQUENCES);
    write_u64(out, sequences_offset);
    write_u64(out, sequence_block_len);
    write_u16(out, 1);

    out.write(reinterpret_cast<const char*>(project_meta.data()),
              static_cast<std::streamsize>(project_meta.size()));
    write_sequences_block(out, input_path, source_file, records);
    out.flush();
    if (!out) {
        throw std::runtime_error("failed while writing SQX output");
    }

    std::cerr << "records=" << records.size()
              << " bases=" << total_bases
              << " output=" << output_path << "\n";
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 3 || argc > 4) {
        std::cerr << "usage: fasta_to_sqx <input.fasta> <output.sqx> [project_name]\n";
        return 2;
    }

    try {
        std::string project_name = argc == 4 ? argv[3] : stem_of(argv[1]);
        auto start = std::chrono::steady_clock::now();
        write_sqx(argv[1], argv[2], project_name);
        auto end = std::chrono::steady_clock::now();
        std::chrono::duration<double> elapsed = end - start;
        std::cerr << "seconds=" << elapsed.count() << "\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "error: " << exc.what() << "\n";
        return 1;
    }
}
