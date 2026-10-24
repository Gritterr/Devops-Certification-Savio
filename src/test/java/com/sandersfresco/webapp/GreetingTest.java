package com.sandersfresco.webapp;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class GreetingTest {

    @Test
    void greetsNamedUser() {
        assertEquals("Hello, DevOps!", Greeting.of("DevOps"));
    }

    @Test
    void trimsWhitespaceAroundName() {
        assertEquals("Hello, Savio!", Greeting.of("  Savio  "));
    }

    @Test
    void fallsBackToWorldWhenNameMissing() {
        assertEquals("Hello, World!", Greeting.of(null));
        assertEquals("Hello, World!", Greeting.of("   "));
    }
}
