package com.sandersfresco.webapp;

/**
 * Builds the greeting text shown by the web application.
 */
public final class Greeting {

    private Greeting() {
    }

    /**
     * Returns a greeting for the given name, or a generic one when the name is blank.
     *
     * @param name the name to greet, may be null
     * @return the greeting message
     */
    public static String of(String name) {
        if (name == null || name.isBlank()) {
            return "Hello, World!";
        }
        return "Hello, " + name.trim() + "!";
    }
}
