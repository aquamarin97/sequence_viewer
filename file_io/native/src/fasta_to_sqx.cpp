#include <array>
#include <chrono>
#include <cstdio>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

namespace fs = std::filesystem;

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

std::string latin1_to_utf8(const std::string& s) {
    std::string out;
    out.reserve(s.size() * 2);
    for (unsigned char c : s) {
        if (c < 0x80) {
            out += static_cast<char>(c);
        } else {
            out += static_cast<char>(0xC0 | (c >> 6));
            out += static_cast<char>(0x80 | (c & 0x3F));
        }
    }
    return out;
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

/* =========================================================
   LUT-BASED IUPAC4 ENCODER
   ========================================================= */

static const std::array<std::uint8_t, 256> IUPAC4_TABLE = []() {
    std::array<std::uint8_t, 256> table{};

    for (std::size_t i = 0; i < table.size(); ++i) {
        table[i] = 0xF;
    }

    table['-'] = 0x0;

    table['A'] = table['a'] = 0x1;
    table['C'] = table['c'] = 0x2;
    table['G'] = table['g'] = 0x3;

    table['T'] = table['t'] = 0x4;
    table['U'] = table['u'] = 0x4;

    table['R'] = table['r'] = 0x5;
    table['Y'] = table['y'] = 0x6;
    table['M'] = table['m'] = 0x7;
    table['K'] = table['k'] = 0x8;
    table['S'] = table['s'] = 0x9;
    table['W'] = table['w'] = 0xA;
    table['H'] = table['h'] = 0xB;
    table['B'] = table['b'] = 0xC;
    table['V'] = table['v'] = 0xD;
    table['D'] = table['d'] = 0xE;

    table['N'] = table['n'] = 0xF;

    return table;
}();

inline std::uint8_t iupac4(unsigned char ch) {
    return IUPAC4_TABLE[ch];
}

/* ========================================================= */

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
            info.header = latin1_to_utf8(trim_ascii(line.substr(1)));
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

std::vector<std::uint8_t> build_project_meta(const std::string& project_name_raw) {
    std::string project_name = latin1_to_utf8(project_name_raw);
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
    write_u32(out, 0);
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
            std::string header = latin1_to_utf8(trim_ascii(line.substr(1)));

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

std::string read_text_file(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot open manifest: " + path.string());
    }
    std::ostringstream buffer;
    buffer << input.rdbuf();
    return buffer.str();
}

std::string json_escape(const std::string& value) {
    std::ostringstream out;
    for (unsigned char ch : value) {
        switch (ch) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\b': out << "\\b"; break;
            case '\f': out << "\\f"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (ch < 0x20) {
                    out << "\\u"
                        << std::hex << std::setw(4) << std::setfill('0')
                        << static_cast<int>(ch)
                        << std::dec << std::setfill(' ');
                } else {
                    out << static_cast<char>(ch);
                }
                break;
        }
    }
    return out.str();
}

std::optional<std::string> json_string_field(const std::string& text,
                                             const std::string& key) {
    const std::string needle = "\"" + key + "\"";
    std::size_t pos = text.find(needle);
    if (pos == std::string::npos) {
        return std::nullopt;
    }
    pos = text.find(':', pos + needle.size());
    if (pos == std::string::npos) {
        return std::nullopt;
    }
    ++pos;
    while (pos < text.size() &&
           (text[pos] == ' ' || text[pos] == '\n' || text[pos] == '\r' || text[pos] == '\t')) {
        ++pos;
    }
    if (pos >= text.size() || text[pos] != '"') {
        return std::nullopt;
    }
    ++pos;

    std::string value;
    bool escaping = false;
    for (; pos < text.size(); ++pos) {
        char ch = text[pos];
        if (escaping) {
            switch (ch) {
                case '"': value.push_back('"'); break;
                case '\\': value.push_back('\\'); break;
                case '/': value.push_back('/'); break;
                case 'b': value.push_back('\b'); break;
                case 'f': value.push_back('\f'); break;
                case 'n': value.push_back('\n'); break;
                case 'r': value.push_back('\r'); break;
                case 't': value.push_back('\t'); break;
                default: value.push_back(ch); break;
            }
            escaping = false;
            continue;
        }
        if (ch == '\\') {
            escaping = true;
            continue;
        }
        if (ch == '"') {
            return value;
        }
        value.push_back(ch);
    }
    return std::nullopt;
}

void write_text_file_atomic(const fs::path& path, const std::string& content) {
    if (!path.parent_path().empty()) {
        fs::create_directories(path.parent_path());
    }

    fs::path temp_path = path;
    temp_path += ".tmp";
    {
        std::ofstream output(temp_path, std::ios::binary | std::ios::trunc);
        if (!output) {
            throw std::runtime_error("cannot open output: " + temp_path.string());
        }
        output << content;
        output.flush();
        if (!output) {
            throw std::runtime_error("failed while writing output: " + temp_path.string());
        }
    }

    std::error_code ec;
    fs::remove(path, ec);
    ec.clear();
    fs::rename(temp_path, path, ec);
    if (ec) {
        throw std::runtime_error("cannot finalize output: " + path.string() + ": " + ec.message());
    }
}

fs::path resolve_job_path(const fs::path& job_dir,
                          const std::string& manifest,
                          const std::string& key,
                          const std::string& default_name) {
    fs::path path = json_string_field(manifest, key).value_or(default_name);
    if (path.is_relative()) {
        path = job_dir / path;
    }
    return path;
}

void write_status(const fs::path& job_dir,
                  const std::string& state,
                  const std::string& step,
                  double progress,
                  const std::string& message) {
    std::ostringstream json;
    json << "{\n"
         << "  \"state\": \"" << json_escape(state) << "\",\n"
         << "  \"step\": \"" << json_escape(step) << "\",\n"
         << "  \"progress\": " << std::fixed << std::setprecision(1) << progress << ",\n"
         << "  \"message\": \"" << json_escape(message) << "\"\n"
         << "}\n";
    write_text_file_atomic(job_dir / "status.json", json.str());
}

void append_event(const fs::path& job_dir,
                  const std::string& level,
                  const std::string& step,
                  double progress,
                  const std::string& message) {
    std::ofstream output(job_dir / "events.ndjson", std::ios::binary | std::ios::app);
    if (!output) {
        throw std::runtime_error("cannot open events log");
    }
    output << "{\"level\":\"" << json_escape(level)
           << "\",\"step\":\"" << json_escape(step)
           << "\",\"progress\":" << std::fixed << std::setprecision(1) << progress
           << ",\"message\":\"" << json_escape(message) << "\"}\n";
}

void write_motif_search_result(const fs::path& result_path,
                               const std::string& job_id,
                               const std::string& manifest_path) {
    std::ostringstream json;
    json << "{\n"
         << "  \"protocol_version\": 1,\n"
         << "  \"job_type\": \"motif-search\",\n"
         << "  \"job_id\": \"" << json_escape(job_id) << "\",\n"
         << "  \"status\": \"skeleton\",\n"
         << "  \"manifest\": \"" << json_escape(manifest_path) << "\",\n"
         << "  \"message\": \"Native motif-search skeleton completed. Algorithm is not implemented yet.\",\n"
         << "  \"hits\": [],\n"
         << "  \"annotations\": []\n"
         << "}\n";
    write_text_file_atomic(result_path, json.str());
}

int run_motif_search_command(const std::string& manifest_path_raw) {
    fs::path manifest_path(manifest_path_raw);
    fs::path job_dir = manifest_path.parent_path();
    if (job_dir.empty()) {
        job_dir = ".";
    }

    try {
        fs::create_directories(job_dir);
        std::string manifest = read_text_file(manifest_path);
        std::string command = json_string_field(manifest, "command").value_or("motif-search");
        if (command != "motif-search") {
            throw std::runtime_error("manifest command must be motif-search");
        }

        std::string job_id = json_string_field(manifest, "job_id").value_or(manifest_path.stem().string());
        fs::path artifacts_dir = resolve_job_path(job_dir, manifest, "artifacts", "artifacts");
        fs::create_directories(artifacts_dir);

        std::cerr << "[NATIVE:MOTIF-SEARCH] manifest=" << manifest_path.string()
                  << " job_id=" << job_id << "\n";
        append_event(job_dir, "info", "startup", 0.0, "Native motif-search job started");
        write_status(job_dir, "running", "manifest", 10.0, "Manifest loaded");

        append_event(job_dir, "info", "skeleton", 50.0, "Motif-search skeleton is ready");
        write_status(job_dir, "running", "skeleton", 50.0, "Native skeleton running");

        fs::path result_path = resolve_job_path(job_dir, manifest, "result", "result.json");
        write_motif_search_result(result_path, job_id, manifest_path.string());

        write_status(job_dir, "succeeded", "complete", 100.0, "Motif-search skeleton completed");
        append_event(job_dir, "info", "complete", 100.0, "Native motif-search job completed");
        std::cerr << "[NATIVE:MOTIF-SEARCH] result=" << result_path.string() << "\n";
        return 0;

    } catch (const std::exception& exc) {
        try {
            write_status(job_dir, "failed", "error", 0.0, exc.what());
            append_event(job_dir, "error", "error", 0.0, exc.what());
        } catch (...) {
        }
        std::cerr << "error: " << exc.what() << "\n";
        return 1;
    }
}

void print_usage(const char* executable) {
    std::cerr
        << "usage:\n"
        << "  " << executable << " fasta-to-sqx <input.fasta> <output.sqx> [project_name]\n"
        << "  " << executable << " motif-search <manifest.json>\n"
        << "  " << executable << " capabilities\n"
        << "  " << executable << " --version\n"
        << "\n"
        << "legacy:\n"
        << "  " << executable << " <input.fasta> <output.sqx> [project_name]\n";
}

void print_capabilities() {
    std::cout
        << "{\n"
        << "  \"app\": \"sequence_viewer_native\",\n"
        << "  \"version\": \"" << APP_VERSION << "\",\n"
        << "  \"protocol_version\": 1,\n"
        << "  \"commands\": [\n"
        << "    {\n"
        << "      \"name\": \"fasta-to-sqx\",\n"
        << "      \"status\": \"stable\",\n"
        << "      \"description\": \"Convert FASTA nucleotide records to SQX project data\"\n"
        << "    },\n"
        << "    {\n"
        << "      \"name\": \"motif-search\",\n"
        << "      \"status\": \"skeleton\",\n"
        << "      \"description\": \"Run a manifest-based native motif search job\"\n"
        << "    }\n"
        << "  ]\n"
        << "}\n";
}

int run_fasta_to_sqx_command(const std::string& input_path,
                             const std::string& output_path,
                             const std::string& project_name) {
    try {
        auto start = std::chrono::steady_clock::now();

        write_sqx(input_path, output_path, project_name);

        auto end = std::chrono::steady_clock::now();
        std::chrono::duration<double> elapsed = end - start;

        std::cerr << "seconds=" << elapsed.count() << "\n";

        return 0;

    } catch (const std::exception& exc) {
        std::cerr << "error: " << exc.what() << "\n";
        return 1;
    }
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 2;
    }

    const std::string command = argv[1];

    if (command == "--help" || command == "help") {
        print_usage(argv[0]);
        return 0;
    }

    if (command == "--version" || command == "version") {
        std::cout << APP_VERSION << "\n";
        return 0;
    }

    if (command == "capabilities") {
        print_capabilities();
        return 0;
    }

    if (command == "fasta-to-sqx") {
        if (argc < 4 || argc > 5) {
            print_usage(argv[0]);
            return 2;
        }
        std::string project_name = argc == 5 ? argv[4] : stem_of(argv[2]);
        return run_fasta_to_sqx_command(argv[2], argv[3], project_name);
    }

    if (command == "motif-search") {
        if (argc != 3) {
            print_usage(argv[0]);
            return 2;
        }
        return run_motif_search_command(argv[2]);
    }

    if (argc == 3 || argc == 4) {
        std::string project_name = argc == 4 ? argv[3] : stem_of(argv[1]);
        return run_fasta_to_sqx_command(argv[1], argv[2], project_name);
    }

    std::cerr << "error: unknown command: " << command << "\n";
    print_usage(argv[0]);
    return 2;
}
