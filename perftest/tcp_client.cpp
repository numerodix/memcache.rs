#include <iostream>
#include <arpa/inet.h>
#include <assert.h>
#include <netdb.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>


using namespace std;

class TcpClient {
    public:
        TcpClient(string host, uint16_t port);
        bool _connect(); // to avoid clashing with imported symbol 'connect'
        bool transmit(const char* data, uint32_t len);
        uint32_t receive(char *buf, uint32_t len);

    private:
        string m_host;
        uint16_t m_port;
        int32_t m_sockfd;
};

TcpClient::TcpClient(string host, uint16_t port) 
    : m_host(host), m_port(port), m_sockfd(-1) {
}

bool TcpClient::_connect() {
    // Already connected
    if (m_sockfd > -1) {
        return true;
    }

    // Create the socket first
    int32_t sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd == -1) {
        perror("Could not create socket");
        return false;
    }

    // Do we need to resolve the hostname?
    struct sockaddr_in server_addr;
    if (inet_addr(m_host.c_str()) == INADDR_NONE) {
        struct hostent *he;
        struct in_addr **addr_list;

        if ((he = gethostbyname(m_host.c_str())) == NULL) {
            perror("gethostbyname");
            cout << "Failed to resolve hostname\n";
            return false;
        }

        addr_list = (struct in_addr**) he->h_addr_list;
        for (int i=0; addr_list[i] != NULL; i++) {
            server_addr.sin_addr = *addr_list[i];
            cout << m_host << " resolved to " << inet_ntoa(*addr_list[i]) << endl;
            break;
        }

    // We have an ip address already
    } else {
        server_addr.sin_addr.s_addr = inet_addr(m_host.c_str());
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(m_port);

    // Establish connection
    if (connect(sockfd, (struct sockaddr*) &server_addr, sizeof(server_addr)) < 0) {
        perror("Connect failed.");
        return false;
    }

    cout << "Connected\n";
    m_sockfd = sockfd;
    return true;
}

bool TcpClient::transmit(const char* data, uint32_t len) {
    assert( this->_connect() == true );

    if (send(m_sockfd, data, strlen(data), 0) < 0) {
        perror("Send failed");
        return false;
    }

    cout << "Data sent.\n";
    return true;
}

uint32_t TcpClient::receive(char* data, uint32_t len) {
    assert( this->_connect() == true );

    ssize_t bytes_cnt = recv(m_sockfd, data, len, 0);
    if (bytes_cnt < 0) {
        perror("recv failed.");
    }

    cout << "Received data.\n";
    return (uint32_t) bytes_cnt;
}


int main() {
    TcpClient cli("127.0.0.1", 11211);
    assert( true == cli._connect() );

    string cmd("stats\r\n");
    assert( true == cli.transmit(cmd.c_str(), cmd.length()) );

    char buf[4096];
    memset(&buf, 0, 4097);
    assert( 0 < cli.receive(buf, 4096) );

    printf("got: %s\n", buf);

    return 0;
}
