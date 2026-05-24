.equ SYS_exit,   1             // Darwin syscall number for exit.
.equ SYS_read,   3             // Darwin syscall number for read.
.equ SYS_write,  4             // Darwin syscall number for write.
.equ SYS_close,  6             // Darwin syscall number for close.
.equ SYS_accept, 30            // Darwin syscall number for accept.
.equ SYS_socket, 97            // Darwin syscall number for socket.
.equ SYS_bind,   104           // Darwin syscall number for bind.
.equ SYS_listen, 106           // Darwin syscall number for listen.

.global _main                  // Export _main so the macOS linker can use it as the program entry point.
.align 2                       // Align the next symbol on a 4-byte boundary, which ARM64 instructions require.

_main:
    stp x29, x30, [sp, #-16]!  // Push the frame pointer (x29) and link register (x30) onto the stack.
    mov x29, sp                // Establish this function's stack frame.

    // socket(AF_INET, SOCK_STREAM, 0)
    mov x0, #2                 // x0 = domain: AF_INET, meaning IPv4.
    mov x1, #1                 // x1 = type: SOCK_STREAM, meaning TCP.
    mov x2, #0                 // x2 = protocol: 0 lets the OS choose the default protocol for TCP.
    mov x16, #SYS_socket       // x16 = Darwin syscall number for socket.
    svc #0x80                  // Enter the kernel; return value arrives in x0.
    b.cs _exit_error           // If carry is set, the syscall failed.
    mov x19, x0                // Save the listening socket fd in x19, a callee-saved register.

    // bind(fd, &addr, 16)
    mov x0, x19                // x0 = listening socket fd.
    adrp x1, _addr@PAGE        // Load the 4KB page address containing _addr into x1.
    add  x1, x1, _addr@PAGEOFF // Add the page offset so x1 points exactly at _addr.
    mov x2, #16                // x2 = sizeof(sockaddr_in) on macOS.
    mov x16, #SYS_bind         // x16 = Darwin syscall number for bind.
    svc #0x80                  // Call bind(fd, &addr, 16) in the kernel.
    b.cs _exit_error           // Exit if bind fails.

    // listen(fd, 8)
    mov x0, x19                // x0 = listening socket fd.
    mov x1, #8                 // x1 = backlog: allow up to 8 queued connections.
    mov x16, #SYS_listen       // x16 = Darwin syscall number for listen.
    svc #0x80                  // Put the socket into passive/server mode.
    b.cs _exit_error           // Exit if listen fails.

_accept_loop:
    // client = accept(fd, NULL, NULL)
    mov x0, x19                // x0 = listening socket fd.
    mov x1, #0                 // x1 = NULL sockaddr pointer; we are ignoring the client's address.
    mov x2, #0                 // x2 = NULL sockaddr length pointer.
    mov x16, #SYS_accept       // x16 = Darwin syscall number for accept.
    svc #0x80                  // Block until a client connects; accepted fd is returned in x0.
    b.cs _exit_error           // Exit if accept fails.
    mov x20, x0                // Save the accepted client fd in x20.

    // read(client, buffer, 1024)
    mov x0, x20                // x0 = accepted client fd.
    adrp x1, _buffer@PAGE      // Load the page address containing _buffer into x1.
    add  x1, x1, _buffer@PAGEOFF // Add the page offset so x1 points exactly at _buffer.
    mov x2, #1024              // x2 = maximum number of bytes to read.
    mov x16, #SYS_read         // x16 = Darwin syscall number for read.
    svc #0x80                  // Read request bytes into _buffer; this demo does not parse them.
    b.cs _close_client         // If read fails, close this client and continue.

    // write(client, response, response_len)
    mov x0, x20                // x0 = accepted client fd.

    adrp x1, _response@PAGE    // Load the page address containing _response into x1.
    add  x1, x1, _response@PAGEOFF // Add the page offset so x1 points exactly at _response.

    adrp x2, _response_end@PAGE // Load the page address containing _response_end into x2.
    add  x2, x2, _response_end@PAGEOFF // Add the page offset so x2 points exactly at _response_end.
    sub  x2, x2, x1            // x2 = response_len, computed as _response_end - _response.

    mov x16, #SYS_write        // x16 = Darwin syscall number for write.
    svc #0x80                  // Write the full HTTP response to the client socket.

    // close(client)
_close_client:
    mov x0, x20                // x0 = accepted client fd.
    mov x16, #SYS_close        // x16 = Darwin syscall number for close.
    svc #0x80                  // Close the client connection after one response.

    b _accept_loop             // Jump back and wait for the next connection.

_exit_error:
    mov x0, #1                 // x0 = process exit status.
    mov x16, #SYS_exit         // x16 = Darwin syscall number for exit.
    svc #0x80                  // Exit the process without calling libc.

.data                           // Begin initialized data: bytes that are embedded in the executable.

// sockaddr_in for macOS:
// sin_len=16
// sin_family=AF_INET
// sin_port=8080, network byte order: 0x1f90
// sin_addr=0.0.0.0
_addr:
    .byte 16                   // sin_len: length of this sockaddr_in structure.
    .byte 2                    // sin_family: AF_INET for IPv4.
    .byte 0x1f, 0x90           // sin_port: 8080 encoded in network byte order.
    .long 0                    // sin_addr: 0.0.0.0, meaning bind on all available interfaces.
    .zero 8                    // sin_zero: padding so the structure is 16 bytes.

_response:
    .ascii "HTTP/1.1 200 OK\r\n"                 // Status line: protocol, status code, reason phrase.
    .ascii "Content-Type: application/json\r\n"   // Header: tell the client the body is JSON.
    .ascii "Content-Length: 13\r\n"               // Header: byte length of the response body below.
    .ascii "Connection: close\r\n"                // Header: tell the client this connection ends after the response.
    .ascii "\r\n"                                 // Blank line: separates HTTP headers from the body.
    .ascii "{\"ok\": true}\n"                     // Body: the JSON payload sent to every request.
_response_end:                                    // Label just past the response, used to compute response length.

.bss                            // Begin zero-initialized storage: reserved memory, not stored as bytes in the file.
_buffer:
    .space 1024                 // Allocate 1024 bytes for the incoming HTTP request.
